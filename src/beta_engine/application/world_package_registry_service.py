"""Discovery and semantic fingerprinting for canonical World Packages."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.infrastructure.world_package_storage import PACKAGE_FORMAT_VERSION, WorldPackageCountryStore
from beta_engine.world_packages import BUILT_IN_WORLD_IDS, OFFICIAL_FAX_WORLD_ID

OFFICIAL_FAX_WORLD_NAME='Official FAX World'
OFFICIAL_FAX_WORLD_DESCRIPTION='Built-in official FAX squash world package.'
OFFICIAL_FAX_WORLD_VERSION='v1'
DEFAULT_WORLD_PACKAGES_ROOT=Path('config/world_packages')
REQUIRED_WORLD_PACKAGE_FILES=('world.json','countries/index.json','geography/continents.json','geography/regions.json','geography/travel_regions.json')

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
   if (self.world_packages_root/world_id).is_dir(): result.append(self._build(self.world_packages_root/world_id, world_id, True))
  seen={x.world_id for x in result}
  for path in self._custom_package_dirs():
   try: record=self._build(path,path.name,False)
   except Exception: continue
   if record.world_id not in seen: result.append(record); seen.add(record.world_id)
  return result
 def get_package(self,world_id):
  normalized=world_id.strip().lower()
  path=(self.world_packages_root/normalized) if normalized in BUILT_IN_WORLD_IDS else (self.world_packages_root/'custom'/normalized)
  if not path.is_dir(): return None
  try:return self._build(path,normalized,normalized in BUILT_IN_WORLD_IDS)
  except Exception:return None
 def get_official_package(self): return self._build(self.world_packages_root/OFFICIAL_FAX_WORLD_ID,OFFICIAL_FAX_WORLD_ID,True)
 def package_dir(self,world_id):
  normalized=world_id.strip().lower(); path=(self.world_packages_root/normalized) if normalized in BUILT_IN_WORLD_IDS else self.world_packages_root/'custom'/normalized
  return path if path.is_dir() else None
 def package_paths(self,world_id):
  path=self.package_dir(world_id); return self._paths_for_dir(path) if path else None
 def official_paths(self): return self.package_paths(OFFICIAL_FAX_WORLD_ID) or {}
 def _build(self,path,expected,builtin):
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
  m=self._read_json(path/'world.json'); keys=('world_id','name','type','status','source','editable','deletable','archivable','version','content_schema_version','package_format_version')
  payload={'world_metadata':{k:m[k] for k in keys if k in m},'countries':WorldPackageCountryStore(path).semantic_payload(),'continents':self._read_json(path/'geography/continents.json'),'regions':self._read_json(path/'geography/regions.json'),'travel_regions':self._read_json(path/'geography/travel_regions.json')}
  if (path/'geography/timezone_areas.json').is_file(): payload['timezone_areas']=self._read_json(path/'geography/timezone_areas.json')
  return payload
 def _custom_package_dirs(self):
  root=self.world_packages_root/'custom'; return sorted((p for p in root.iterdir() if p.is_dir()),key=lambda p:p.name) if root.is_dir() else []
 def _paths_for_dir(self,p): return {'package_root':p,'world':p/'world.json','countries_root':p/'countries','countries_index':p/'countries/index.json','continents':p/'geography/continents.json','regions':p/'geography/regions.json','travel_regions':p/'geography/travel_regions.json','timezone_areas':p/'geography/timezone_areas.json'}
 def _storage_summary(self,p):
  q=self._paths_for_dir(p); return WorldPackageStorageSummary(*(str(q[k]) for k in ('package_root','world','countries_root','countries_index')) ,str(p/'geography'),*(str(q[k]) for k in ('continents','regions','travel_regions','timezone_areas')))
 def _read_json(self,p):
  value=json.loads(p.read_text());
  if not isinstance(value,dict): raise ValueError(f'{p} must contain object')
  return value
 def _items(self,p,k):
  value=self._read_json(p).get(k,[]); return value if isinstance(value,list) else []
