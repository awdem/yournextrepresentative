from io import StringIO
from time import sleep

import boto3
import pandas as pd
from django.conf import settings
from django.core.management import call_command
from official_documents.models import OfficialDocument, TextractResult
from pdfminer.pdftypes import PDFException
from sopn_parsing.helpers.pdf_helpers import SOPNDocument
from sopn_parsing.helpers.text_helpers import NoTextInDocumentError
from sopn_parsing.models import AWSTextractParsedSOPN


def extract_pages_for_ballot(ballot):
    """
    Try to extract the page numbers for the latest SOPN document related to this
    ballot.

    Because documents can apply to more than one ballot, we also perform
    "drive by" parsing of other ballots contained in a given document.

    :type ballot: candidates.models.Ballot

    """
    try:
        sopn = SOPNDocument(
            file=ballot.sopn.uploaded_file,
            source_url=ballot.sopn.source_url,
            election_date=ballot.election.election_date,
        )
        call_command(
            "sopn_parsing_aws_textract", "--start-analysis", "--get-results"
        )
        return sopn.match_all_pages()
    except NoTextInDocumentError:
        raise NoTextInDocumentError(
            f"Failed to extract pages for {ballot.sopn.uploaded_file.path} as a NoTextInDocumentError was raised"
        )
    except PDFException:
        print(
            f"{ballot.ballot_paper_id} failed to parse as a PDFSyntaxError was raised"
        )
        raise PDFException(
            f"Failed to extract pages for {ballot.sopn.uploaded_file.path} as a PDFSyntaxError was raised"
        )


textract_client = boto3.client(
    "textract", region_name=settings.TEXTRACT_S3_BUCKET_REGION
)


class TextractSOPNHelper:
    """Get the AWS Textract results for a given SOPN."""

    def __init__(
        self, official_document: OfficialDocument, bucket_name: str = None
    ):
        self.official_document = official_document
        # TO DO: set a policy to delete the files from S3 after a certain period
        self.bucket_name = bucket_name or settings.TEXTRACT_S3_BUCKET_NAME

    @property
    def s3_key(self) -> str:
        """
        Return the S3 key for this file (made up of ballot ID?)
        """
        region = settings.TEXTRACT_S3_BUCKET_REGION
        bucket_name = settings.TEXTRACT_S3_BUCKET_NAME
        self.s3_client = boto3.client("s3", region_name=region)
        object_key = str(self.official_document.ballot_id)
        return object_key, bucket_name

    def upload_to_s3(self):
        object_key, bucket_name = self.s3_key

        # TO DO: for dev env, we need a local file_path to upload to S3
        try:
            file_path = self.official_document.uploaded_file.path
        except ValueError:
            raise ValueError(
                f"File path for {self.official_document.ballot.ballot_paper_id} not found"
            )
        with open(file_path, "rb") as file:
            file_bytes = bytearray(file.read())

        response = self.s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_bytes,
        )
        print(f"Uploaded bytes to s3://{bucket_name}/{object_key}")
        return response

    def start_detection(self, replace=False):
        qs = TextractResult.objects.filter(
            official_document=self.official_document
        ).exclude(json_response="")
        if not replace and qs.exists():
            return None
        self.upload_to_s3()
        response = self.textract_start_document_analysis()
        textract_result, _ = TextractResult.objects.update_or_create(
            official_document=self.official_document,
            json_response="",
            job_id=response["JobId"],
        )
        return textract_result

    def textract_start_document_analysis(self):
        return textract_client.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": settings.TEXTRACT_S3_BUCKET_NAME,
                    "Name": str(self.official_document.ballot_id),
                }
            },
            FeatureTypes=["TABLES", "FORMS"],
            OutputConfig={
                "S3Bucket": "public-sopns",
                "S3Prefix": "test",
            },
        )

    def textract_get_document_analysis(self, job_id):
        return textract_client.get_document_analysis(JobId=job_id)

    def update_job_status(self, blocking=False):
        COMPLETED_STATES = ("SUCCEEDED", "FAILED", "PARTIAL_SUCCESS")
        status = self.official_document.textract_result.analysis_status
        if status in COMPLETED_STATES:
            return None
        textract_result = self.official_document.textract_result
        job_id = textract_result.job_id

        response = self.textract_get_document_analysis(job_id)
        while response["JobStatus"] not in [
            "SUCCEEDED",
            "FAILED",
            "PARTIAL_SUCCESS",
        ]:
            sleep(5)
            self.textract_get_document_analysis(job_id)

        if response["JobStatus"] == "SUCCEEDED":
            # update_or_create method returned error
            textract_result.analysis_status = "SUCCEEDED"
            textract_result.json_response = response
            textract_result.save()
        else:
            textract_result.analysis_status = "FAILED"
            textract_result.save()
        return textract_result


class TextractSOPNParsingHelper:
    """Helper class to parse the AWS Textract blocks for a given SOPN
    and return the results as a dataframe. This is not to be confused with
    the SOPN parsing functionality that matches fields including
    candidates to parties."""

    def map_blocks(self, blocks, block_type):
        return {
            block["Id"]: block
            for block in blocks
            if block["BlockType"] == block_type
        }

    def get_children_ids(self, block):
        for rels in block.get("Relationships", []):
            if rels["Type"] == "CHILD":
                yield from rels["Ids"]

    def get_rows_columns_map(self, table_result, blocks_map):
        rows = {}
        scores = []
        for relationship in table_result["Relationships"]:
            if relationship["Type"] == "CHILD":
                for child_id in relationship["Ids"]:
                    cell = blocks_map[child_id]
                    if cell["BlockType"] == "CELL":
                        row_index = cell["RowIndex"]
                        col_index = cell["ColumnIndex"]
                        if row_index not in rows:
                            # create new row
                            rows[row_index] = {}

                        # get confidence score
                        scores.append(str(cell["Confidence"]))

                        # get the text value
                        rows[row_index][col_index] = self.get_text(
                            cell, blocks_map
                        )
        return rows, scores

    def get_text(self, result, blocks_map):
        text = ""
        if "Relationships" in result:
            for relationship in result["Relationships"]:
                if relationship["Type"] == "CHILD":
                    for child_id in relationship["Ids"]:
                        word = blocks_map[child_id]
                        if word["BlockType"] == "WORD":
                            if (
                                "," in word["Text"]
                                and word["Text"].replace(",", "").isnumeric()
                            ):
                                text += '"' + word["Text"] + '"' + " "
                            else:
                                text += word["Text"] + " "
                        if (
                            word["BlockType"] == "SELECTION_ELEMENT"
                            and word["SelectionStatus"] == "SELECTED"
                        ):
                            text += "X "
        return text

    def get_table_csv_results(self, textract_result, official_document):
        blocks = textract_result["Blocks"]
        csv = ""
        blocks_map = {}
        table_blocks = []
        for block in blocks:
            blocks_map[block["Id"]] = block
            if block["BlockType"] == "TABLE":
                table_blocks.append(block)

        if len(table_blocks) <= 0:
            return "<b> NO Table FOUND </b>"

        csv = ""
        for index, table in enumerate(table_blocks):
            csv += self.generate_table_csv(
                table, blocks_map, index + 1, official_document
            )

        return csv

    def generate_table_csv(
        self, table_result, blocks_map, table_index, official_document
    ):
        rows, scores = self.get_rows_columns_map(table_result, blocks_map)

        table_id = "Table_" + str(table_index)

        # get cells.
        csv = "Table: {0}\n\n".format(table_id)

        for row_index, cols in rows.items():
            for col_index, text in cols.items():
                col_indices = len(cols.items())
                csv += "{}".format(text) + ","
            csv += "\n"

        csv += "\n\n Confidence Scores % (Table Cell) \n"
        cols_count = 0
        for score in scores:
            cols_count += 1
            csv += score + ","
            if cols_count == col_indices:
                csv += "\n"
                cols_count = 0

        csv += "\n\n\n"
        # convert csv to pandas dataframe
        df = pd.read_csv(StringIO(csv))

        if df.empty:
            raise Exception(
                f"Failed to parse {official_document} as a pandas dataframe"
            )
        aws_textract_parsed_sopn = AWSTextractParsedSOPN.objects.filter(
            sopn=official_document
        )
        if aws_textract_parsed_sopn:
            aws_textract_parsed_sopn[0].raw_data = df.to_json()
            aws_textract_parsed_sopn[0].save()
        return csv
