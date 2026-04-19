from pathlib import Path


def test_build_generation_manifest_filters_zero_byte_and_labels_sources(tmp_path: Path) -> None:
    from training.generation.build_manifest import build_generation_manifest

    local_dir = tmp_path / "local"
    local_dir.mkdir(parents=True)
    good = local_dir / "tower.png"
    bad = local_dir / "empty.png"
    good.write_bytes(b"fake-image")
    bad.write_bytes(b"")

    rows = build_generation_manifest(
        public_roots=[],
        local_roots=[local_dir],
        external_roots=[],
    )

    assert len(rows) == 1
    assert rows[0]["source_group"] == "local"
    assert rows[0]["path"].endswith("tower.png")


def test_build_generation_manifest_uses_path_tokens_for_caption(tmp_path: Path) -> None:
    from training.generation.build_manifest import build_generation_manifest

    public_dir = tmp_path / "public" / "transmission_line" / "insulator"
    public_dir.mkdir(parents=True)
    (public_dir / "sample.png").write_bytes(b"real-image")

    rows = build_generation_manifest(
        public_roots=[tmp_path / "public"],
        local_roots=[],
        external_roots=[],
    )

    assert len(rows) == 1
    assert (
        rows[0]["caption"]
        == "realistic utility inspection photography, electric power transmission line, insulator equipment"
    )


def test_build_generation_manifest_dedupes_exact_duplicate_files(tmp_path: Path) -> None:
    from training.generation.build_manifest import build_generation_manifest

    external_dir = tmp_path / "external" / "substation"
    external_dir.mkdir(parents=True)
    duplicate_bytes = b"same-image"
    (external_dir / "a.png").write_bytes(duplicate_bytes)
    (external_dir / "b.png").write_bytes(duplicate_bytes)

    rows = build_generation_manifest(
        public_roots=[],
        local_roots=[],
        external_roots=[tmp_path / "external"],
    )

    assert len(rows) == 1
    assert rows[0]["path"].endswith("a.png")
