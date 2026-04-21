"""Unit tests for Pydantic request/response models."""

import pytest
from pydantic import ValidationError

from src.models.document_classify_request_model import DocumentClassifyRequest
from src.models.document_classify_response_model import DocumentClassifyResponse
from src.models.add_classification_type_request_model import AddClassificationTypeRequest


class TestDocumentClassifyRequest:
    def test_valid_request(self):
        req = DocumentClassifyRequest(
            document_name="invoice.pdf",
            request="classify this document",
            image_bytes=["fakebytes"],
        )
        assert req.document_name == "invoice.pdf"
        assert req.request == "classify this document"
        assert req.image_bytes == ["fakebytes"]

    def test_missing_document_name_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyRequest(request="classify", image_bytes=b"data")

    def test_missing_request_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyRequest(document_name="file.pdf", image_bytes=b"data")

    def test_missing_image_bytes_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyRequest(document_name="file.pdf", request="classify")

    def test_empty_bytes_accepted(self):
        req = DocumentClassifyRequest(
            document_name="empty.pdf", request="classify", image_bytes=[b""]
        )
        assert req.image_bytes == [""]

    def test_all_fields_required(self):
        with pytest.raises(ValidationError):
            DocumentClassifyRequest()


class TestDocumentClassifyResponse:
    def test_valid_response(self):
        resp = DocumentClassifyResponse(
            document_name="invoice.pdf",
            classification_type="Invoice",
            confidence_score=0.95,
            reasoning="Contains invoice header and payment terms.",
        )
        assert resp.document_name == "invoice.pdf"
        assert resp.classification_type == "Invoice"
        assert resp.confidence_score == 0.95
        assert resp.reasoning == "Contains invoice header and payment terms."

    def test_confidence_score_zero(self):
        resp = DocumentClassifyResponse(
            document_name="doc.pdf",
            classification_type="Unknown",
            confidence_score=0.0,
            reasoning="No match.",
        )
        assert resp.confidence_score == 0.0

    def test_confidence_score_one(self):
        resp = DocumentClassifyResponse(
            document_name="doc.pdf",
            classification_type="Invoice",
            confidence_score=1.0,
            reasoning="Exact match.",
        )
        assert resp.confidence_score == 1.0

    def test_invalid_confidence_score_string_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyResponse(
                document_name="doc.pdf",
                classification_type="Invoice",
                confidence_score="high",
                reasoning="test",
            )

    def test_missing_classification_type_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyResponse(
                document_name="doc.pdf",
                confidence_score=0.9,
                reasoning="test",
            )

    def test_missing_document_name_raises(self):
        with pytest.raises(ValidationError):
            DocumentClassifyResponse(
                classification_type="Invoice",
                confidence_score=0.9,
                reasoning="test",
            )


class TestAddClassificationTypeRequest:
    def test_valid_with_description(self):
        req = AddClassificationTypeRequest(
            classification_type="Invoice",
            description="A document requesting payment for goods or services.",
        )
        assert req.classification_type == "Invoice"
        assert req.description == "A document requesting payment for goods or services."

    def test_valid_without_description_defaults_none(self):
        req = AddClassificationTypeRequest(classification_type="Referral")
        assert req.classification_type == "Referral"
        assert req.description is None

    def test_missing_classification_type_raises(self):
        with pytest.raises(ValidationError):
            AddClassificationTypeRequest(description="Some description")

    def test_empty_string_classification_type(self):
        req = AddClassificationTypeRequest(classification_type="")
        assert req.classification_type == ""
