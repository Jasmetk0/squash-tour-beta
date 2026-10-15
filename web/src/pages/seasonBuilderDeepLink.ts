export function selectedBuilderSeason(
 requested:string|null,
 seasons:readonly {label:string}[]
):string|null {
 if(!requested || !/^20\d{2}\/\d{2}$/.test(requested))return null
 const start=Number(requested.slice(0,4))
 const end=Number(requested.slice(5))
 if(start<2000||start>2049||end!==(start+1)%100)return null
 return seasons.find(x=>x.label===requested)?.label??null
}
