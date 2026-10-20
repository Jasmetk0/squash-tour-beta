"""Discovery and semantic fingerprinting for canonical World Packages."""
from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.package_evidence_files import canonical_json_sha256, load_json_object, safe_package_file
from beta_engine.infrastructure.world_package_storage import PACKAGE_FORMAT_VERSION, WorldPackageCountryStore
from beta_engine.world_packages import BUILT_IN_WORLD_IDS, OFFICIAL_FAX_WORLD_ID

OFFICIAL_FAX_WORLD_NAME='Official FAX World'
OFFICIAL_FAX_WORLD_DESCRIPTION='Built-in official FAX squash world package.'
OFFICIAL_FAX_WORLD_VERSION='v1'
DEFAULT_WORLD_PACKAGES_ROOT=Path('config/world_packages')
REQUIRED_WORLD_PACKAGE_FILES=('world.json','countries/index.json','geography/continents.json','geography/regions.json','geography/travel_regions.json')
# IDs are directory components, including when received from an HTTP route.
_WORLD_ID = re.compile(r"[a-z0-9][a-z0-9_]{2,63}", re.ASCII)


def _canonical_world_id(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if _WORLD_ID.fullmatch(normalized) else None

@dataclass(frozen=True)
class WorldPackageStorageSummary:
 package_root_path:str; world_metadata_path:str; countries_root_path:str; countries_index_path:str; geography_root_path:str; continents_path:str; regions_path:str; travel_regions_path:str; timezone_areas_path:str
@dataclass(frozen=True)
class WorldPackageRegistryRecord:
 world_id:str; name:str; description:str; type:str; status:str; source:str; editable:bool; deletable:bool; archivable:bool; version:str; fingerprint:str; country_count:int; continent_count:int; region_count:int; travel_region_count:int; timezone_area_count:int; used_by_run_count:int|None; validation_status:str; storage:WorldPackageStorageSummary
@dataclass(slots=True)
class WorldPackageRegistryService:
 countries_service: CountriesConfigService|None=None
 manual_overrides_service: ManualPlayerOverridesService|None=None
 world_packages_root: Path=DEFAULT_WORLD_PACKAGES_ROOT
 def __post_init__(self): self.world_packages_root=Path(self.world_packages_root)
 def list_packages(self):
  result=[]
  for world_id in BUILT_IN_WORLD_IDS:
   path=self.package_dir(world_id)
   if path is not None: result.append(self._build(path, world_id, True))
  seen={x.world_id for x in result}
  for path in self._custom_package_dirs():
   try: record=self._build(path,path.name,False)
   except Exception: continue
   if record.world_id not in seen: result.append(record); seen.add(record.world_id)
  return result
 def get_package(self,world_id):
  normalized=_canonical_world_id(world_id)
  if normalized is None: return None
  path=self.package_dir(normalized)
  if path is None: return None
  try:return self._build(path,normalized,normalized in BUILT_IN_WORLD_IDS)
  except Exception:return None
 def get_official_package(self):
  path=self.package_dir(OFFICIAL_FAX_WORLD_ID)
  if path is None: raise ValueError("official World Package directory is unavailable")
  return self._build(path,OFFICIAL_FAX_WORLD_ID,True)
 def package_dir(self,world_id):
  normalized=_canonical_world_id(world_id)
  if normalized is None: return None
  parent=self.world_packages_root if normalized in BUILT_IN_WORLD_IDS else self.world_packages_root/'custom'
  if parent.is_symlink() or not parent.is_dir(): return None
  # Select an actual child discovered from the trusted root; never append a
  # URL-provided name to a filesystem path, even after format validation.
  for candidate in parent.iterdir():
   if candidate.name != normalized or candidate.is_symlink() or not candidate.is_dir(): continue
   try:
    if candidate.resolve().parent != parent.resolve(): continue
   except (OSError,RuntimeError): continue
   return candidate
  return None
 def package_paths(self,world_id):
  path=self.package_dir(world_id); return self._paths_for_dir(path) if path else None
 def official_paths(self): return self.package_paths(OFFICIAL_FAX_WORLD_ID) or {}
 def _build(self,path,expected,builtin):
  safe_path=self.package_dir(expected)
  if safe_path is None or path != safe_path: raise ValueError("World Package path escapes its registered directory")
  if not all((path/name).is_file() for name in REQUIRED_WORLD_PACKAGE_FILES): raise ValueError(f'{path} is incomplete')
  m=self._read_json(path/'world.json')
  if m.get('world_id')!=expected: raise ValueError('world_id mismatch')
  if m.get('package_format_version')!=PACKAGE_FORMAT_VERSION: raise ValueError('unsupported package format')
  if builtin and (m.get('type')!='official' or m.get('source')!='built_in'): raise ValueError('built-in metadata mismatch')
  if not builtin and (m.get('type')!='custom' or m.get('source')!='custom_config'): raise ValueError('custom metadata mismatch')
  countries=WorldPackageCountryStore(path).load_config()
  return WorldPackageRegistryRecord(world_id=expected,name=str(m['name']),description=str(m.get('description','')),type=str(m['type']),status=str(m['status']),source=str(m['source']),editable=bool(m['editable']),deletable=bool(m['deletable']),archivable=bool(m['archivable']),version=str(m['version']),fingerprint=self._fingerprint(path),country_count=len(countries.countries),continent_count=len(self._items(path/'geography/continents.json','continents')),region_count=len(self._items(path/'geography/regions.json','regions')),travel_region_count=len(self._items(path/'geography/travel_regions.json','travel_regions')),timezone_area_count=len(self._items(path/'geography/timezone_areas.json','timezone_areas')) if (path/'geography/timezone_areas.json').is_file() else 0,used_by_run_count=None,validation_status='valid',storage=self._storage_summary(path))
 def _fingerprint(self,path): return hashlib.sha256(json.dumps(self._fingerprint_payload(path),sort_keys=True,separators=(',',':')).encode()).hexdigest()
 def _fingerprint_payload(self,path):
  m=self._read_json(path/'world.json'); keys=('world_id','name','type','status','source','editable','deletable','archivable','version','content_schema_version','package_format_version','rating_scale','rating_years','data_cutoff')
  payload={'world_metadata':{k:m[k] for k in keys if k in m},'countries':WorldPackageCountryStore(path).semantic_payload(),'continents':self._read_json(path/'geography/continents.json'),'regions':self._read_json(path/'geography/regions.json'),'travel_regions':self._read_json(path/'geography/travel_regions.json')}
  if (path/'geography/timezone_areas.json').is_file(): payload['timezone_areas']=self._read_json(path/'geography/timezone_areas.json')
  player_identity=path/'generation/player_identity.json'
  if player_identity.is_file(): payload['player_identity']=self._read_json(player_identity)
  source_dir=path/'generation/sources'
  if source_dir.is_dir():
   payload['country_rating_sources']={
    p.stem:canonical_json_sha256(
     load_json_object(safe_package_file(path,p.relative_to(path).as_posix()))
    ) for p in sorted(source_dir.glob('*.json'))
   }
  else:
   rating_sources=path/'generation/country_rating_sources.json'
   if rating_sources.is_file(): payload['country_rating_sources']=self._read_json(rating_sources)
  manifest_dir=path/'generation/observation_manifests'
  if manifest_dir.is_dir():
   manifests={
    p.stem:load_json_object(safe_package_file(path,p.relative_to(path).as_posix()))
    for p in sorted(manifest_dir.glob('*.json'))
   }
  else:
   rating_observations=path/'generation/country_rating_observation_datasets.json'
   manifests=self._read_json(rating_observations) if rating_observations.is_file() else {}
  if manifests:
   payload['country_rating_observation_datasets']={
    dataset_id:canonical_json_sha256(manifest) for dataset_id,manifest in sorted(manifests.items())
   }
   payload['country_rating_observation_files']={
    dataset_id:canonical_json_sha256(load_json_object(safe_package_file(path,str(manifest.get('relative_path','')))))
    for dataset_id,manifest in sorted(manifests.items()) if isinstance(manifest,dict)
   }
  calibration_dir=path/'generation/calibration'
  if calibration_dir.is_dir():
   payload['country_rating_calibration_files']={
    p.name:canonical_json_sha256(
     load_json_object(safe_package_file(path,p.relative_to(path).as_posix()))
    ) for p in sorted(calibration_dir.glob('*.json'))
   }
  else:
   calibration_catalog=path/'generation/country_rating_calibration_models.json'
   if calibration_catalog.is_file():
    catalog=self._read_json(calibration_catalog); payload['country_rating_calibration_models']=catalog
    models=catalog.get('models')
    if not isinstance(models,dict): raise ValueError('calibration catalogue models must be an object')
    payload['country_rating_calibration_files']={
     model_id:canonical_json_sha256(load_json_object(safe_package_file(path,str(declaration.get('relative_path','')))))
     for model_id,declaration in sorted(models.items()) if isinstance(declaration,dict)
    }
  return payload
 def _custom_package_dirs(self):
  root=self.world_packages_root/'custom'
  if not root.is_dir() or root.is_symlink(): return []
  return sorted((p for p in root.iterdir() if _canonical_world_id(p.name) == p.name and p.is_dir() and not p.is_symlink()),key=lambda p:p.name)
 def _paths_for_dir(self,p): return {'package_root':p,'world':p/'world.json','countries_root':p/'countries','countries_index':p/'countries/index.json','continents':p/'geography/continents.json','regions':p/'geography/regions.json','travel_regions':p/'geography/travel_regions.json','timezone_areas':p/'geography/timezone_areas.json'}
 def _storage_summary(self,p):
  q=self._paths_for_dir(p); return WorldPackageStorageSummary(*(str(q[k]) for k in ('package_root','world','countries_root','countries_index')) ,str(p/'geography'),*(str(q[k]) for k in ('continents','regions','travel_regions','timezone_areas')))
 def _read_json(self,p):
  # Every registry JSON read is confined to the configured World Packages root.
  # The shared resolver rejects absolute paths, traversal and linked components.
  source=Path(p)
  try:
   relative=source.relative_to(self.world_packages_root).as_posix()
  except ValueError as exc:
   raise ValueError("World Package metadata is outside the registered root") from exc
  trusted=safe_package_file(self.world_packages_root,relative)
  value=json.loads(trusted.read_text(encoding='utf-8'))
  if not isinstance(value,dict): raise ValueError(f'{source} must contain object')
  return value
 def _items(self,p,k):
  value=self._read_json(p).get(k,[]); return value if isinstance(value,list) else []
