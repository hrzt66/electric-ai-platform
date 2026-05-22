from __future__ import annotations

"""Build the image-2 electric object dataset with project generation runtimes."""

import argparse
import hashlib
import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

try:
    from bootstrap import ensure_project_root_on_path
except ModuleNotFoundError:  # pragma: no cover - used when imported as scripts.* in tests
    from scripts.bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from app.core.runtime_logging import configure_runtime_logging
from app.runtimes.runtime_registry import RuntimeRegistry
from app.schemas.jobs import GenerateJob
from app.services.generation_service import GenerationService

configure_runtime_logging()
logger = logging.getLogger("electric_ai.batch.image2")


DEFAULT_OUTPUT_ROOT = Path("/Users/hrzt/code/vibe coding/codex/毕业设计/image-2")
DEFAULT_ASSET_SERVICE_URL = "http://127.0.0.1:8084"
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, artifact, distorted geometry, watermark, text"

MODEL_TARGETS: dict[str, int] = {
    "sd15-electric": 50,
    "ssd1b-electric": 50,
    "sd15-electric-specialized": 50,
    "gpt-image-2": 15,
}


@dataclass(frozen=True)
class CategorySpec:
    slug: str
    prompt: str
    aliases: tuple[str, ...]


CATEGORY_SPECS: tuple[CategorySpec, ...] = (
    CategorySpec(
        slug="photovoltaic_farm",
        prompt="photovoltaic farm, large solar panel arrays, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("photovoltaic farm", "photovoltaic_farm", "solar farm", "solar plant", "solar-plants"),
    ),
    CategorySpec(
        slug="transmission_tower",
        prompt="transmission tower, high voltage power line tower, realistic electric grid infrastructure, clear daylight, high detail",
        aliases=("transmission_tower", "transmission tower", "power line tower", "powerline"),
    ),
    CategorySpec(
        slug="wind_turbine",
        prompt="wind turbine, wind farm power generation facility, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("wind_turbine", "wind turbine", "wind turbines", "wind farm", "wind-turbine"),
    ),
    CategorySpec(
        slug="dam",
        prompt="hydroelectric dam, concrete dam power station, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("dam", "hydroelectric dam", "hydropower"),
    ),
    CategorySpec(
        slug="substation",
        prompt="electrical substation, transformers and switchgear yard, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("substation", "electrical substation", "switchgear"),
    ),
    CategorySpec(
        slug="thermal_power_plant",
        prompt="thermal power plant, cooling towers and industrial generation units, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("thermal_power_plant", "thermal power plant", "coal power plant", "power plant"),
    ),
    CategorySpec(
        slug="nuclear_power_plant",
        prompt="nuclear power plant, reactor buildings and cooling towers, realistic electric power infrastructure, clear daylight, high detail",
        aliases=("nuclear_power_plant", "nuclear power plant", "nuclear plant"),
    ),
)


@dataclass(frozen=True)
class ExistingAsset:
    category: str
    model_name: str
    file_path: Path
    positive_prompt: str
    seed: int | None = None


@dataclass(frozen=True)
class Plan:
    existing_count: int
    copy_count: int
    generate_count: int


@dataclass
class ManifestRecord:
    category: str
    model_name: str
    file_path: str
    source: str
    prompt: str
    seed: int | None = None
    original_file_path: str | None = None


def normalize_text(value: str) -> str:
    return value.lower().replace("_", " ").replace("-", " ").strip()


def classify_asset_category(prompt: str) -> str | None:
    normalized = normalize_text(prompt)
    for spec in CATEGORY_SPECS:
        if any(normalize_text(alias) in normalized for alias in spec.aliases):
            return spec.slug
    return None


def category_prompt(category: str) -> str:
    for spec in CATEGORY_SPECS:
        if spec.slug == category:
            return spec.prompt
    raise KeyError(category)


def next_output_path(output_root: Path, category: str, model_name: str) -> Path:
    target_dir = output_root / category / model_name
    target_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{category}_{model_name}_"
    used: set[int] = set()
    for path in target_dir.glob(f"{prefix}*.png"):
        suffix = path.stem.removeprefix(prefix)
        if suffix.isdigit():
            used.add(int(suffix))
    index = 1
    while index in used:
        index += 1
    return target_dir / f"{prefix}{index:03d}.png"


def stable_seed(*, seed_base: int, category: str, model_name: str, index: int) -> int:
    payload = f"{seed_base}:{category}:{model_name}:{index}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:12], 16) % 2_000_000_000 + 1


def iter_batch_seeds(*, seed_base: int, category: str, model_name: str, start_count: int, batch_size: int) -> list[int]:
    return [
        stable_seed(seed_base=seed_base, category=category, model_name=model_name, index=start_count + offset)
        for offset in range(batch_size)
    ]


class BatchPlanner:
    def __init__(self, *, output_root: Path) -> None:
        self.output_root = output_root

    def plan(
        self,
        *,
        category: str,
        model_name: str,
        target_count: int,
        existing_outputs: list[Path],
        reusable_assets: list[ExistingAsset],
    ) -> Plan:
        existing_count = len(existing_outputs)
        remaining_after_existing = max(target_count - existing_count, 0)
        copy_count = min(remaining_after_existing, len(reusable_assets))
        generate_count = max(target_count - existing_count - copy_count, 0)
        return Plan(existing_count=existing_count, copy_count=copy_count, generate_count=generate_count)


def list_existing_outputs(output_root: Path, category: str, model_name: str) -> list[Path]:
    target_dir = output_root / category / model_name
    if not target_dir.exists():
        return []
    return sorted(path for path in target_dir.glob("*.png") if path.is_file())


def read_manifest(output_root: Path) -> list[ManifestRecord]:
    manifest_path = output_root / "manifest.jsonl"
    if not manifest_path.exists():
        return []
    records: list[ManifestRecord] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        records.append(ManifestRecord(**data))
    return records


def append_manifest(output_root: Path, records: list[ManifestRecord]) -> None:
    if not records:
        return
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def fetch_history_assets(asset_service_url: str, *, page_size: int = 100) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=10.0) as client:
        page = 1
        while True:
            response = client.get(
                f"{asset_service_url.rstrip('/')}/api/v1/assets/history/page",
                params={"page": page, "page_size": page_size},
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or {}
            page_items = data.get("items") or []
            items.extend(page_items)
            total_pages = int(data.get("total_pages") or 0)
            if page >= total_pages:
                break
            page += 1
    return items


def reusable_assets_from_history(items: list[dict[str, Any]]) -> list[ExistingAsset]:
    assets: list[ExistingAsset] = []
    for item in items:
        model_name = str(item.get("model_name") or "")
        if model_name not in MODEL_TARGETS:
            continue
        prompt = str(item.get("positive_prompt") or "")
        category = classify_asset_category(prompt)
        if category is None:
            continue
        file_path = Path(str(item.get("file_path") or ""))
        if not file_path.is_file():
            continue
        seed_value = item.get("seed")
        seed = int(seed_value) if isinstance(seed_value, int | float | str) and str(seed_value).isdigit() else None
        assets.append(
            ExistingAsset(
                category=category,
                model_name=model_name,
                file_path=file_path,
                positive_prompt=prompt,
                seed=seed,
            )
        )
    return assets


def copy_reusable_asset(output_root: Path, asset: ExistingAsset) -> ManifestRecord:
    destination = next_output_path(output_root, asset.category, asset.model_name)
    shutil.copy2(asset.file_path, destination)
    return ManifestRecord(
        category=asset.category,
        model_name=asset.model_name,
        file_path=str(destination),
        source="asset-service",
        prompt=asset.positive_prompt,
        seed=asset.seed,
        original_file_path=str(asset.file_path),
    )


def generate_one(
    *,
    service: GenerationService,
    runtime: object,
    output_root: Path,
    category: str,
    model_name: str,
    job_id: int,
    seed: int,
    width: int,
    height: int,
    steps: int,
    guidance_scale: float,
) -> ManifestRecord:
    prompt = category_prompt(category)
    job = GenerateJob(
        job_id=job_id,
        prompt=prompt,
        negative_prompt=DEFAULT_NEGATIVE_PROMPT,
        model_name=model_name,
        seed=seed,
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        num_images=1,
    )
    generated = service.generate(job, runtime)
    if not generated:
        raise RuntimeError(f"runtime returned no image: category={category} model={model_name}")
    source_path = Path(generated[0]["file_path"])
    destination = next_output_path(output_root, category, model_name)
    shutil.copy2(source_path, destination)
    return ManifestRecord(
        category=category,
        model_name=model_name,
        file_path=str(destination),
        source="generated",
        prompt=prompt,
        seed=int(generated[0].get("seed", seed)),
        original_file_path=str(source_path),
    )


def generate_batch(
    *,
    service: GenerationService,
    runtime: object,
    output_root: Path,
    category: str,
    model_name: str,
    job_id: int,
    seeds: list[int],
    width: int,
    height: int,
    steps: int,
    guidance_scale: float,
) -> list[ManifestRecord]:
    if model_name == "gpt-image-2":
        records: list[ManifestRecord] = []
        for index, seed in enumerate(seeds):
            records.append(
                generate_one(
                    service=service,
                    runtime=runtime,
                    output_root=output_root,
                    category=category,
                    model_name=model_name,
                    job_id=job_id + index,
                    seed=seed,
                    width=width,
                    height=height,
                    steps=steps,
                    guidance_scale=guidance_scale,
                )
            )
        return records

    prompt = category_prompt(category)
    job = GenerateJob(
        job_id=job_id,
        prompt=prompt,
        negative_prompt=DEFAULT_NEGATIVE_PROMPT,
        model_name=model_name,
        seed=seeds[0],
        steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        num_images=len(seeds),
    )
    generated = service.generate(job, runtime)
    if len(generated) != len(seeds):
        raise RuntimeError(
            f"runtime returned {len(generated)} images for {len(seeds)} seeds: category={category} model={model_name}"
        )

    records: list[ManifestRecord] = []
    for index, item in enumerate(generated):
        source_path = Path(item["file_path"])
        destination = next_output_path(output_root, category, model_name)
        shutil.copy2(source_path, destination)
        records.append(
            ManifestRecord(
                category=category,
                model_name=model_name,
                file_path=str(destination),
                source="generated",
                prompt=prompt,
                seed=int(item.get("seed", seeds[index])),
                original_file_path=str(source_path),
            )
        )
    return records


def run_batch(args: argparse.Namespace) -> None:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    history_items: list[dict[str, Any]] = []
    if not args.skip_asset_service:
        try:
            history_items = fetch_history_assets(args.asset_service_url)
            logger.info("loaded %s history assets from asset service", len(history_items))
        except Exception as exc:
            logger.warning("asset service history unavailable, continuing with generation only: %s", exc)

    manifest_records = read_manifest(output_root)
    manifest_generated = {
        (record.category, record.model_name, Path(record.file_path).name)
        for record in manifest_records
        if Path(record.file_path).is_file()
    }
    reusable_assets = reusable_assets_from_history(history_items)
    planner = BatchPlanner(output_root=output_root)
    registry = RuntimeRegistry()
    generation_service = GenerationService()
    appended: list[ManifestRecord] = []
    base_job_id = int(time.strftime("%Y%m%d%H%M%S"))

    try:
        for spec in CATEGORY_SPECS:
            category = spec.slug
            for model_name, target_count in MODEL_TARGETS.items():
                existing_outputs = list_existing_outputs(output_root, category, model_name)
                existing_names = {path.name for path in existing_outputs}
                for path in existing_outputs:
                    key = (category, model_name, path.name)
                    if key not in manifest_generated:
                        appended.append(
                            ManifestRecord(
                                category=category,
                                model_name=model_name,
                                file_path=str(path),
                                source="existing-output",
                                prompt=spec.prompt,
                            )
                        )
                        manifest_generated.add(key)

                model_assets = [
                    asset
                    for asset in reusable_assets
                    if asset.category == category
                    and asset.model_name == model_name
                    and asset.file_path.name not in existing_names
                ]
                plan = planner.plan(
                    category=category,
                    model_name=model_name,
                    target_count=target_count,
                    existing_outputs=existing_outputs,
                    reusable_assets=model_assets,
                )
                logger.info(
                    "category=%s model=%s existing=%s copy=%s generate=%s target=%s",
                    category,
                    model_name,
                    plan.existing_count,
                    plan.copy_count,
                    plan.generate_count,
                    target_count,
                )

                for asset in model_assets[: plan.copy_count]:
                    appended.append(copy_reusable_asset(output_root, asset))
                    append_manifest(output_root, appended)
                    appended.clear()

                if plan.generate_count <= 0:
                    continue

                runtime = registry.get_generation_runtime(model_name)
                try:
                    while True:
                        current_count = len(list_existing_outputs(output_root, category, model_name))
                        if current_count >= target_count:
                            break
                        remaining = target_count - current_count
                        batch_size = min(args.batch_size, remaining)
                        seeds = iter_batch_seeds(
                            seed_base=args.seed_base,
                            category=category,
                            model_name=model_name,
                            start_count=current_count,
                            batch_size=batch_size,
                        )
                        job_id = base_job_id + len(read_manifest(output_root)) + current_count + 1
                        records = generate_batch(
                            service=generation_service,
                            runtime=runtime,
                            output_root=output_root,
                            category=category,
                            model_name=model_name,
                            job_id=job_id,
                            seeds=seeds,
                            width=args.width,
                            height=args.height,
                            steps=args.steps,
                            guidance_scale=args.guidance_scale,
                        )
                        appended.extend(records)
                        append_manifest(output_root, appended)
                        appended.clear()
                        logger.info(
                            "saved category=%s model=%s count=%s/%s path=%s",
                            category,
                            model_name,
                            current_count + len(records),
                            target_count,
                            records[-1].file_path,
                        )
                finally:
                    registry.release_generation_runtime(model_name)
    finally:
        append_manifest(output_root, appended)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/copy the requested image-2 electric object dataset.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--asset-service-url", default=DEFAULT_ASSET_SERVICE_URL)
    parser.add_argument("--skip-asset-service", action="store_true")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--seed-base", type=int, default=20260509)
    parser.add_argument("--batch-size", type=int, default=4)
    return parser.parse_args()


if __name__ == "__main__":
    run_batch(parse_args())
