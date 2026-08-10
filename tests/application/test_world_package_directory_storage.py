import json, shutil
from pathlib import Path
import pytest
from beta_engine.application.world_package_clone_service import WorldPackageCloneService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService
from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.infrastructure.world_package_storage import ATTRIBUTE_NAMES, WorldPackageCountryStore


def test_official_germanica_is_losslessly_materialized():
 c=WorldPackageCountryStore(Path('config/world_packages/official_fax_world')).load_country('GER')
 assert (c.code,c.name,c.population,c.area_km2)==('GER','Germanica',169702055,870516)
 assert (c.wealth_support,c.squash_popularity,c.squash_tradition,c.system_quality)==(5,3,3,5)
 assert (c.competition_density,c.federation_quality,c.court_count,c.travel_region)==(4.0,5.0,1800,'EUROPE')
 assert c.style_dna=={} and c.notes


def test_real_world_timelines_include_large_country_kosovo_and_fallback():
 store=WorldPackageCountryStore(Path('config/world_packages/real_world'))
 for code in ('USA','XKX','ALA'):
  c=store.load_country(code)
  assert c.population==c.population_by_year[2020]
  assert c.population_by_year[1955]>0 and c.population_by_year[2050]>0


def test_semantic_fingerprint_ignores_format_and_index_order_but_tracks_attribute(tmp_path):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root)
 original=registry.get_official_package().fingerprint
 index=root/'official_fax_world/countries/index.json'; data=json.loads(index.read_text()); data['country_codes'].reverse(); index.write_text(json.dumps(data,separators=(',',':')))
 assert registry.get_official_package().fingerprint==original
 attribute=root/'official_fax_world/countries/GER/attributes/squash_popularity.json'; data=json.loads(attribute.read_text()); data['value']=4; attribute.write_text(json.dumps(data,indent=8))
 assert registry.get_official_package().fingerprint!=original


def test_clone_recursively_preserves_directory_country_storage(tmp_path):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 result=WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='example_world',name='Example',description=None,dry_run=False)
 assert result.ok and result.validation and result.validation.status=='valid'
 target=root/'custom/example_world'; assert (target/'countries/GER/attributes/population.json').is_file()
 assert not (target/'countries.json').exists()
 assert WorldPackageCountryStore(target).load_country('GER')==WorldPackageCountryStore(root/'official_fax_world').load_country('GER')


def _scalar_country(*, name='Alpha'):
 return Country(code='AAA',name=name,region='EUROPE',population=1_234_567,wealth_support=3,squash_popularity=4,squash_tradition=2,system_quality=5)


def test_scalar_population_country_roundtrips_through_write_and_update(tmp_path):
 store=WorldPackageCountryStore(tmp_path/'custom_world')
 store.replace_dataset(CountriesConfig(dataset_status='test',countries=[_scalar_country()]))
 first=store.load_country('AAA')
 assert first.population==1_234_567
 assert first.default_population_year==2020
 assert first.default_population==1_234_567
 assert first.population_by_year=={2020:1_234_567}
 store.write_country(_scalar_country(name='Alpha Updated'))
 second=store.load_country('AAA')
 assert second.name=='Alpha Updated'
 assert second.population_by_year=={2020:1_234_567}


def test_replace_dataset_restores_live_countries_when_stage_promotion_fails(tmp_path,monkeypatch):
 store=WorldPackageCountryStore(tmp_path/'custom_world')
 store.replace_dataset(CountriesConfig(dataset_status='original',countries=[_scalar_country()]))
 original_rename=Path.rename
 def fail_stage_promotion(path,target):
  if path.name=='countries' and path.parent.name.startswith('.countries-stage-'):
   raise OSError('simulated promotion failure')
  return original_rename(path,target)
 monkeypatch.setattr(Path,'rename',fail_stage_promotion)
 with pytest.raises(OSError,match='simulated promotion failure'):
  store.replace_dataset(CountriesConfig(dataset_status='replacement',countries=[_scalar_country(name='Replacement')]))
 restored=store.load_config()
 assert restored.dataset_status=='original'
 assert restored.countries[0].name=='Alpha'


def test_editable_custom_package_countries_are_not_reported_read_only(tmp_path):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 result=WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='editable_world',name='Editable',description=None,dry_run=False)
 assert result.ok
 countries=WorldPackageCountriesService(registry).get_countries('editable_world')
 assert countries is not None and countries.read_only is False


def test_clone_removes_target_and_fails_when_final_validation_has_errors(tmp_path,monkeypatch):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 invalid=WorldPackageValidationResult('invalid_world','errors',1,0,0,[])
 monkeypatch.setattr(WorldPackageValidationService,'validate_package',lambda self,_world_id: invalid)
 result=WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='invalid_world',name='Invalid',description=None,dry_run=False)
 assert result.ok is False
 assert result.validation is invalid
 assert not (root/'custom/invalid_world').exists()
 assert (root/'official_fax_world').is_dir()


def test_only_canonical_world_package_root_exists_and_all_attributes_present():
 assert Path('config/world_packages').is_dir(); assert not Path('config/world').exists(); assert not Path('config/worlds').exists()
 country=Path('config/world_packages/official_fax_world/countries/GER/attributes')
 assert {p.stem for p in country.glob('*.json')}=={'population',*ATTRIBUTE_NAMES}
