from pathlib import Path

from app.utils.file_helpers import delete_files_if_exist, metadata_file_paths


def test_metadata_file_paths_returns_original_and_transformed(tmp_path):
    paths = metadata_file_paths(str(tmp_path), "private/members/1/idp-1-metadata.xml")

    assert paths == [
        str(tmp_path / "private/members/1/idp-1-metadata.xml"),
        str(tmp_path / "private/members/1/idp-1-metadata-transformed.xml"),
    ]


def test_metadata_file_paths_rejects_traversal(tmp_path):
    assert metadata_file_paths(str(tmp_path), "../secret.xml") == []


def test_delete_files_if_exist_is_best_effort(tmp_path):
    target = tmp_path / "metadata.xml"
    target.write_text("<xml/>", encoding="utf-8")

    delete_files_if_exist([str(target), str(tmp_path / "missing.xml")])

    assert not target.exists()
