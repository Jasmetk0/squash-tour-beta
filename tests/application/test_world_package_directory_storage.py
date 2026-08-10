import json, shutil
from dataclasses import replace
from pathlib import Path
import pytest
from beta_engine.application.world_package_clone_service import WorldPackageCloneService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService, WorldPackageCountryUpdate, WorldPackageCountryPopulationUpdate, WorldPackageMutationError
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


def test_replace_country_preserves_index_population_and_cleans_artifacts(tmp_path):
 store=WorldPackageCountryStore(tmp_path/'world'); store.replace_dataset(CountriesConfig(dataset_status='test',countries=[_scalar_country()]))
 index=store.index_path.read_bytes(); population=(store.countries_root/'AAA/attributes/population.json').read_bytes()
 store.replace_country(_scalar_country(name='Alpha Prime'))
 assert store.load_country('AAA').name=='Alpha Prime'
 assert store.index_path.read_bytes()==index
 assert (store.countries_root/'AAA/attributes/population.json').read_bytes()==population
 assert not list(store.countries_root.glob('.AAA-*'))


def test_replace_country_restores_live_country_when_promotion_fails(tmp_path,monkeypatch):
 store=WorldPackageCountryStore(tmp_path/'world'); store.replace_dataset(CountriesConfig(dataset_status='test',countries=[_scalar_country()]))
 original_rename=Path.rename
 def fail(path,target):
  if path.name=='AAA' and path.parent.name=='countries' and path.parent.parent.name.startswith('.AAA-stage-'): raise OSError('promotion failed')
  return original_rename(path,target)
 monkeypatch.setattr(Path,'rename',fail)
 with pytest.raises(OSError,match='promotion failed'): store.replace_country(_scalar_country(name='Broken'))
 assert store.load_country('AAA').name=='Alpha'


def test_custom_country_edit_changes_fingerprint_and_preserves_population(tmp_path):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 assert WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='editable',name='Editable',description=None,dry_run=False).ok
 service=WorldPackageCountriesService(registry,validation); before=registry.get_package('editable'); original=service.get_country('editable','GER').country
 update=WorldPackageCountryUpdate(**{**original.model_dump(include={'name','notes','area_km2','region','travel_region','wealth_support','squash_popularity','squash_tradition','system_quality','competition_density','federation_quality','court_count','style_dna'}), 'name':'Germanica Prime','squash_popularity':4,'style_dna':{'pace':1.25},'expected_package_fingerprint':before.fingerprint})
 result=service.update_country('editable','GER',update); after=result.detail.country
 assert (after.code,after.name,after.squash_popularity,after.style_dna)==('GER','Germanica Prime',4,{'pace':1.25})
 assert after.population_by_year==original.population_by_year and result.validation.status=='valid'
 assert result.detail.package.fingerprint!=before.fingerprint
 with pytest.raises(WorldPackageMutationError) as exc: service.update_country('official_fax_world','GER',update)
 assert exc.value.status_code==403


@pytest.mark.parametrize('world_id',['official_fax_world','real_world'])
def test_builtin_country_edit_is_rejected_even_if_editable_metadata_is_true(tmp_path,monkeypatch,world_id):
 root=tmp_path/'packages'; shutil.copytree(f'config/world_packages/{world_id}',root/world_id)
 registry=WorldPackageRegistryService(world_packages_root=root); package=registry.get_package(world_id)
 monkeypatch.setattr(WorldPackageRegistryService,'get_package',lambda self,candidate: replace(package,editable=True) if candidate==world_id else None)
 country=WorldPackageCountryStore(root/world_id).load_config().countries[0]
 payload=WorldPackageCountryUpdate(**country.model_dump(include={'name','notes','area_km2','region','travel_region','wealth_support','squash_popularity','squash_tradition','system_quality','competition_density','federation_quality','court_count','style_dna'}))
 with pytest.raises(WorldPackageMutationError) as exc: WorldPackageCountriesService(registry).update_country(world_id,country.code,payload)
 assert exc.value.status_code==403


def test_country_edit_restores_original_after_final_validation_errors(tmp_path,monkeypatch):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 assert WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='editable',name='Editable',description=None,dry_run=False).ok
 store=WorldPackageCountryStore(root/'custom/editable'); original=store.load_country('GER'); index=store.index_path.read_bytes()
 payload=WorldPackageCountryUpdate(**{**original.model_dump(include={'name','notes','area_km2','region','travel_region','wealth_support','squash_popularity','squash_tradition','system_quality','competition_density','federation_quality','court_count','style_dna'}),'name':'Must Roll Back'})
 invalid=WorldPackageValidationResult('editable','errors',1,0,0,[])
 monkeypatch.setattr(WorldPackageValidationService,'validate_package',lambda self,_world_id: invalid)
 with pytest.raises(WorldPackageMutationError,match='leave the World Package invalid'): WorldPackageCountriesService(registry,validation).update_country('editable','GER',payload)
 assert store.load_country('GER')==original
 assert store.index_path.read_bytes()==index
 assert not list(store.countries_root.glob('.GER-*'))
 assert registry.get_package('editable') is not None


def test_population_replacement_changes_only_population_and_materializes_default(tmp_path):
 store=WorldPackageCountryStore(tmp_path/'world'); store.replace_dataset(CountriesConfig(dataset_status='test',countries=[_scalar_country()]))
 files={path.relative_to(store.package_root):path.read_bytes() for path in store.package_root.rglob('*.json')}
 store.replace_population('AAA',{1995:900_000,2020:2_000_000})
 country=store.load_country('AAA')
 assert country.population_by_year=={1995:900_000,2020:2_000_000}
 assert country.population==country.default_population==2_000_000
 changed={path for path,data in files.items() if (store.package_root/path).read_bytes()!=data}
 assert changed=={Path('countries/AAA/attributes/population.json')}
 assert not list((store.countries_root/'AAA/attributes').glob('.population.json.*'))


def test_population_service_fingerprint_non_default_and_rollback(tmp_path,monkeypatch):
 root=tmp_path/'packages'; shutil.copytree('config/world_packages/official_fax_world',root/'official_fax_world')
 registry=WorldPackageRegistryService(world_packages_root=root); validation=WorldPackageValidationService(registry)
 assert WorldPackageCloneService(registry,validation).clone_official_world(new_world_id='editable',name='Editable',description=None,dry_run=False).ok
 service=WorldPackageCountriesService(registry,validation); before=service.get_country('editable','GER'); fingerprint=before.package.fingerprint
 result=service.update_population('editable','GER',WorldPackageCountryPopulationUpdate(values_by_year={1995:100,2020:before.country.population},expected_package_fingerprint=fingerprint))
 assert result.detail.country.population==before.country.population and result.detail.country.population_by_year[1995]==100
 assert result.detail.package.fingerprint!=fingerprint
 original=(root/'custom/editable/countries/GER/attributes/population.json').read_bytes()
 invalid=WorldPackageValidationResult('editable','errors',1,0,0,[])
 monkeypatch.setattr(WorldPackageValidationService,'validate_package',lambda self,_world_id: invalid)
 with pytest.raises(WorldPackageMutationError,match='leave the World Package invalid'):
  service.update_population('editable','GER',WorldPackageCountryPopulationUpdate(values_by_year={2020:999}))
 assert (root/'custom/editable/countries/GER/attributes/population.json').read_bytes()==original
