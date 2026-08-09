"""Fail-closed validation for canonical World Package directories."""
from __future__ import annotations
import json,re
from dataclasses import dataclass
from typing import Literal
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.infrastructure.world_package_storage import ATTRIBUTE_NAMES, COUNTRIES_INDEX_SCHEMA, PACKAGE_FORMAT_VERSION, WorldPackageCountryStore
ValidationSeverity=Literal['info','warning','error']; ValidationCheckStatus=Literal['passed','warning','failed']; ValidationStatus=Literal['valid','warnings','errors']
@dataclass(frozen=True)
class WorldPackageValidationCheck: code:str; severity:ValidationSeverity; status:ValidationCheckStatus; message:str; path:str|None=None; field:str|None=None
@dataclass(frozen=True)
class WorldPackageValidationResult: world_id:str; status:ValidationStatus; error_count:int; warning_count:int; info_count:int; checks:list[WorldPackageValidationCheck]
@dataclass(slots=True)
class WorldPackageValidationService:
 registry_service:WorldPackageRegistryService
 def validate_package(self,world_id):
  world_id=world_id.strip().lower(); root=self.registry_service.package_dir(world_id)
  if root is None:return None
  checks=[]
  def ok(code,msg,path):checks.append(WorldPackageValidationCheck(code,'info','passed',msg,str(path)))
  def bad(code,msg,path):checks.append(WorldPackageValidationCheck(code,'error','failed',f'{world_id}: {msg}',str(path)))
  world_path=root/'world.json'
  try:
   world=json.loads(world_path.read_text()); assert isinstance(world,dict)
   if world.get('world_id')!=world_id: bad('world_metadata_valid',f'world.json world_id does not match {world_id}',world_path)
   elif world.get('package_format_version')!=PACKAGE_FORMAT_VERSION: bad('package_format_supported',f"unsupported package format {world.get('package_format_version')!r}",world_path)
   else: ok('world_metadata_valid','world.json metadata and package format are valid.',world_path)
  except Exception as exc: bad('world_metadata_json_valid',f'world.json is malformed: {exc}',world_path); world={}
  store=WorldPackageCountryStore(root); index_path=store.index_path; countries=[]
  try:
   raw=json.loads(index_path.read_text()); codes=raw.get('country_codes') if isinstance(raw,dict) else None
   if raw.get('schema_version')!=COUNTRIES_INDEX_SCHEMA: raise ValueError(f"unsupported schema_version {raw.get('schema_version')!r}")
   if not isinstance(codes,list) or not codes: raise ValueError('country_codes must be non-empty')
   if len(codes)!=len(set(codes)): raise ValueError('duplicate country code')
   if any(not isinstance(c,str) or re.fullmatch(r'[A-Z]{3}',c) is None for c in codes): raise ValueError('codes must be three uppercase letters')
   orphans=sorted(p.name for p in store.countries_root.iterdir() if p.is_dir() and p.name not in codes and not p.name.startswith('.'))
   if orphans: bad('country_orphans_valid',f'orphan country directories: {orphans}',store.countries_root)
   else: ok('country_orphans_valid','No orphan country directories.',store.countries_root)
   for code in codes:
    try:countries.append(store.load_country(code))
    except Exception as exc:bad('country_valid',f'{code}: {exc}',store.countries_root/code)
   ok('countries_index_valid',f'countries/index.json lists {len(codes)} countries.',index_path)
  except Exception as exc: bad('countries_index_valid',f'countries/index.json is invalid: {exc}',index_path); codes=[]
  def collection(name):
   path=root/'geography'/f'{name}.json'
   try:
    data=json.loads(path.read_text()); items=data[name]
    if not isinstance(items,list):raise ValueError(f'{name} must be an array')
    return path,items,{x.get('code') for x in items if isinstance(x,dict)}
   except Exception as exc:bad(f'{name}_valid',f'{path.name} is invalid: {exc}',path); return path,[],set()
  cp,continents,continent_codes=collection('continents'); rp,regions,region_codes=collection('regions'); tp,travels,travel_codes=collection('travel_regions')
  for region in regions:
   if isinstance(region,dict) and region.get('continent_code') is not None and region.get('continent_code') not in continent_codes: bad('region_continent_reference',f"regions.json {region.get('code')} references unknown continent {region.get('continent_code')}",rp)
  for country in countries:
   if country.region not in region_codes: bad('country_region_reference',f'{country.code}/attributes/region.json references unknown Region {country.region}',root/'countries'/country.code/'attributes/region.json')
   if country.travel_region is not None and country.travel_region not in travel_codes: bad('country_travel_region_reference',f'{country.code}/attributes/travel_region.json references unknown Travel Region {country.travel_region}',root/'countries'/country.code/'attributes/travel_region.json')
   coverage=world.get('population_years')
   if isinstance(coverage,dict):
    required=set(range(coverage.get('from',0),coverage.get('to',-1)+1))
    if not required.issubset(country.population_by_year):bad('population_coverage_valid',f'{country.code}/attributes/population.json lacks declared population years {sorted(required-set(country.population_by_year))}',root/'countries'/country.code/'attributes/population.json')
  if isinstance(world.get('population_years'),dict) and not any(c.code=='population_coverage_valid' and c.status=='failed' for c in checks):
   ok('population_coverage_valid','All countries preserve the declared population timeline.',store.countries_root)
  errors=sum(c.severity=='error' for c in checks); warnings=sum(c.severity=='warning' for c in checks); infos=sum(c.severity=='info' for c in checks)
  return WorldPackageValidationResult(world_id,'errors' if errors else 'warnings' if warnings else 'valid',errors,warnings,infos,checks)
