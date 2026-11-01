/** Dedicated read-only Saved Revision Cross-Run/Branch Compare A/B. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useParams,useSearchParams} from 'react-router-dom'
import {
  compareCrossSavedRevisions
} from '../api/client'
import type {CrossSavedRevisionComparison} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {useLanguage} from '../i18n/LanguageContext'
import {historyText} from '../i18n/historyText'

import {projectCrossSavedStateComparison, type CompareResult} from './savedCompareStates'

export function SavedCrossRunComparePage():JSX.Element{
  const {language}=useLanguage()
  const T=(english:string)=>historyText(english,language)
  const [params,setParams]=useSearchParams()
  const requestedRunA=params.get('run_a')??''
  const requestedBranchA=params.get('branch_a')??''
  const requestedRevA=params.get('rev_a')??''
  const requestedRunB=params.get('run_b')??''
  const requestedBranchB=params.get('branch_b')??''
  const requestedRevB=params.get('rev_b')??''
  const view=params.get('filter')==='all'?'all':'differences'

  const [inputRunA,setInputRunA]=useState(requestedRunA)
  const [inputBranchA,setInputBranchA]=useState(requestedBranchA)
  const [inputRevA,setInputRevA]=useState(requestedRevA)

  const [inputRunB,setInputRunB]=useState(requestedRunB)
  const [inputBranchB,setInputBranchB]=useState(requestedBranchB)
  const [inputRevB,setInputRevB]=useState(requestedRevB)

  const canCompare=Boolean(requestedRunA&&requestedBranchA&&requestedRevA&&
    requestedRunB&&requestedBranchB&&requestedRevB)

  const comparisonQuery=useQuery({
    queryKey:['cross-saved-states-compare',requestedRunA,requestedBranchA,requestedRevA,requestedRunB,requestedBranchB,requestedRevB],
    queryFn:()=>compareCrossSavedRevisions(requestedRunA,requestedBranchA,requestedRevA,requestedRunB,requestedBranchB,requestedRevB),
    enabled:canCompare,retry:false
  })

  const apply=()=>{
    setParams({
      run_a:inputRunA,branch_a:inputBranchA,rev_a:inputRevA,
      run_b:inputRunB,branch_b:inputBranchB,rev_b:inputRevB,
      filter:view
    })
  }
  const swap=()=>{
    setInputRunA(inputRunB);setInputBranchA(inputBranchB);setInputRevA(inputRevB)
    setInputRunB(inputRunA);setInputBranchB(inputBranchA);setInputRevB(inputRevA)
    setParams({
      run_a:requestedRunB,branch_a:requestedBranchB,rev_a:requestedRevB,
      run_b:requestedRunA,branch_b:requestedBranchA,rev_b:requestedRevA,
      filter:view
    })
  }

  const compared=canCompare&&comparisonQuery.data?
    projectCrossSavedStateComparison(comparisonQuery.data):null
  const rows=compared?.rows.filter(r=>view==='all'||r.status!=='unchanged')??[]

  return <div className="cross-compare-page">
    <header className="page-header">
      <h1>{T('Cross-Run Saved Comparison')}</h1>
      <p className="read-only-badge">{T('Read-only Viewer')}</p>
    </header>

    <div className="compare-controls">
      <div className="compare-side compare-a">
        <h3>{T('Source A')}</h3>
        <label>Run ID: <input type="text" value={inputRunA} onChange={e=>setInputRunA(e.target.value)} /></label>
        <label>Branch ID: <input type="text" value={inputBranchA} onChange={e=>setInputBranchA(e.target.value)} /></label>
        <label>Revision ID: <input type="text" value={inputRevA} onChange={e=>setInputRevA(e.target.value)} /></label>
      </div>

      <div className="compare-actions">
        <button type="button" onClick={swap} className="btn-swap">{T('Swap A/B')}</button>
        <button type="button" onClick={apply} className="btn-primary">{T('Compare')}</button>
      </div>

      <div className="compare-side compare-b">
        <h3>{T('Source B')}</h3>
        <label>Run ID: <input type="text" value={inputRunB} onChange={e=>setInputRunB(e.target.value)} /></label>
        <label>Branch ID: <input type="text" value={inputBranchB} onChange={e=>setInputBranchB(e.target.value)} /></label>
        <label>Revision ID: <input type="text" value={inputRevB} onChange={e=>setInputRevB(e.target.value)} /></label>
      </div>
    </div>

    {comparisonQuery.isFetching&&<div className="loading" role="status">{T('Loading comparison...')}</div>}
    {comparisonQuery.isError&&<div className="error-message">
      {formatApiError(comparisonQuery.error)}
    </div>}

    {comparisonQuery.isSuccess&&!compared&&<div className="error-message">
      {T('Invalid comparison payload from server.')}
    </div>}

    {compared&&<div className="compare-results">
      <div className="compare-summary">
        <h4>{T('Changes overview')}</h4>
        <ul>
          <li>{T('Run metadata changes:')} {compared.runChanges}</li>
          <li>{T('Branch metadata changes:')} {compared.branchChanges}</li>
          <li>{T('Total components matched:')} {compared.components}</li>
          <li>{T('Components changed:')} {compared.changed}</li>
        </ul>
        <div className="filter-controls">
          <label>
            <input type="radio" name="filter" checked={view==='differences'}
              onChange={()=>setParams(p=>{p.set('filter','differences');return p})} />
            {T('Differences only')}
          </label>
          <label>
            <input type="radio" name="filter" checked={view==='all'}
              onChange={()=>setParams(p=>{p.set('filter','all');return p})} />
            {T('All valid data')}
          </label>
        </div>
      </div>

      <table className="compare-table">
        <thead>
          <tr>
            <th>{T('Section')}</th>
            <th>{T('Key')}</th>
            <th>{T('Status')}</th>
            <th>{T('Before (A)')}</th>
            <th>{T('After (B)')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row=><tr key={row.id} className={`status-${row.status}`}>
            <td>{row.section}</td>
            <td>{row.key}</td>
            <td>{T(row.status.toUpperCase())}</td>
            <td>{row.before===undefined||row.before===null?'-':String(row.before)}</td>
            <td>{row.after===undefined||row.after===null?'-':String(row.after)}</td>
          </tr>)}
          {rows.length===0&&<tr>
            <td colSpan={5} className="empty-state">{T('No differences found.')}</td>
          </tr>}
        </tbody>
      </table>
    </div>}
  </div>
}
