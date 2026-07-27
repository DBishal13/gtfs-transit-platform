import zipfile
from pathlib import Path

import pytest

from pipeline.ingest.gtfs_loader import load_gtfs

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mini_gtfs"


@pytest.fixture(scope="session")
def mini_gtfs_zip(tmp_path_factory) -> Path:
    zip_path = tmp_path_factory.mktemp("gtfs") / "mini_gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for txt_file in FIXTURE_DIR.glob("*.txt"):
            zf.write(txt_file, arcname=txt_file.name)
    return zip_path


@pytest.fixture(scope="session")
def mini_feed(mini_gtfs_zip):
    return load_gtfs(mini_gtfs_zip, feed_id="mini-test")
