import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  deleteRunFollow, getFollowAlerts, getRunFollows, putAlertState, putRunFollow
} from '../api/client'
import { validAlertList, validFollowList } from '../api/followNotifications'
import type { AlertItem } from '../api/followNotifications'
import { formatApiError } from '../utils/apiErrors'
import { readerPage, readerPageCount, readerSlice, useReaderParams } from './readerUrlState'

type Props = { runId: string; branchId: string; savedHead: string; cs: boolean }

const KIND: Record<string, [string, string]> = {
  turn_pro: ['Přechod mezi profesionály', 'Turned professional'],
  first_recorded_title: ['První zaznamenaný titul', 'First recorded title'],
  first_top_rank: ['První zaznamenané TOP 100', 'First recorded TOP 100'],
  career_high_ranking: ['Nejlepší publikovaný ranking', 'Career-high published ranking'],
  retirement: ['Konec kariéry', 'Retirement']
}
const REASON = (r: string, cs: boolean): string => {
  if (r.startsWith('player:')) return cs ? 'sledovaný hráč' : 'followed player'
  if (r.endsWith(':domestic_leader')) return cs ? 'sledovaná země: domácí špička' : 'followed country: domestic leader'
  if (r.endsWith(':exceptional_individual')) return cs ? 'sledovaná země: mimořádný individuální výsledek' : 'followed country: exceptional individual result'
  return r
}
const when = (w: { season_index: number; week: number }, cs: boolean) =>
  `${cs ? 'sezóna' : 'season'} ${w.season_index + 1} · ${cs ? 'týden' : 'week'} ${w.week}`

export function FollowAlertsPanel({ runId, branchId, savedHead, cs }: Props): JSX.Element {
  const client = useQueryClient()
  const [kind, setKind] = useState<'player' | 'country'>('player')
  const [subject, setSubject] = useState('')
  const url = useReaderParams('alert', JSON.stringify([runId, branchId, savedHead]))
  const showHidden = url.get('hidden') === 'true'
  const search = url.get('search').toLocaleLowerCase()
  const stateValue = url.get('state', 'all')
  const stateFilter = ['all', 'unread', 'read', 'hidden'].includes(stateValue) ? stateValue : 'all'
  const eventFilter = url.get('event', 'all')
  const order = url.get('order', 'desc')
  const page = readerPage(url.get('page', '1'))
  const followsKey = ['run-follows', runId]
  const follows = useQuery({ queryKey: followsKey, queryFn: () => getRunFollows(runId), retry: false })
  const list = follows.data && validFollowList(follows.data, runId) ? follows.data : null
  // Alerts depend on the follow set: it is part of the key and the read waits for it, so a
  // slow first read can never leave a stale "no alerts" result after a follow changed.
  const signature = list ? list.follows.map(f => `${f.kind}:${f.subject_id}:${f.alerts_enabled}`).join('|') : null
  const alertsKey = ['follow-alerts', runId, branchId, savedHead, showHidden, signature]
  const alerts = useQuery({
    queryKey: alertsKey, queryFn: () => getFollowAlerts(runId, branchId, showHidden),
    enabled: list !== null, retry: false
  })
  const refresh = () => {
    void client.invalidateQueries({ queryKey: followsKey })
    void client.invalidateQueries({ queryKey: ['follow-alerts', runId, branchId] })
  }
  const follow = useMutation({
    mutationFn: (v: { kind: string; id: string; enabled: boolean }) => putRunFollow(runId, v.kind, v.id, v.enabled),
    onSuccess: refresh
  })
  const unfollow = useMutation({ mutationFn: (v: { kind: string; id: string }) => deleteRunFollow(runId, v.kind, v.id), onSuccess: refresh })
  const mark = useMutation({
    mutationFn: (v: { key: string; state: 'unread' | 'read' | 'hidden'; seen: number }) => putAlertState(runId, branchId, v.key, v.state, v.seen),
    onSuccess: refresh
  })
  const title = cs ? 'Sledování a upozornění' : 'Following and alerts'
  const cards = alerts.data && validAlertList(alerts.data, { runId, branchId, savedHead }) ? alerts.data : null
  const filtered = (cards?.cards ?? []).map((value, index) => ({ value, index }))
    .filter(({ value }) =>
      (stateFilter === 'all' || value.state === stateFilter) &&
      (eventFilter === 'all' || value.items.some(item => item.kind === eventFilter)) &&
      [value.player_name, value.player_id, value.country_code].join(' ').toLocaleLowerCase().includes(search))
    .sort((a, b) => {
      const diff = a.value.last_week.season_index - b.value.last_week.season_index ||
        a.value.last_week.week - b.value.last_week.week ||
        a.value.first_week.season_index - b.value.first_week.season_index ||
        a.value.first_week.week - b.value.first_week.week
      return (order === 'asc' ? diff : -diff) || a.index - b.index
    })
  const pages = readerPageCount(filtered.length)
  const current = Math.min(page, pages)
  const visible = readerSlice(filtered, current)
  const eventKinds = Array.from(new Set((cards?.cards ?? []).flatMap(card => card.items.map(item => item.kind)))).sort()
  const label = (it: AlertItem) => (KIND[it.kind] ?? [it.kind, it.kind])[cs ? 0 : 1]
  const detail = (it: AlertItem) => {
    const d = it.detail
    if (it.kind === 'first_top_rank' || it.kind === 'career_high_ranking') return ` · #${String(d.rank)}`
    if (it.kind === 'retirement' && d.without_turn_pro === true) return cs ? ' · bez přechodu mezi profesionály' : ' · without ever turning pro'
    return ''
  }
  return <section aria-label={title}>
    <h2>{title}</h2>
    <p>{cs
      ? 'Sledování je předvolba celého Runu (platí pro všechny Branche) a není součástí Saved revize. Upozornění se odvozují z doložených kariérních faktů vybrané Branch; čtení, skrytí ani ztišení nic nemaže a neovlivňuje simulaci.'
      : 'Following is a Run-wide preference (shared by all Branches) and is not Saved Run content. Alerts are derived from the selected Branch’s recorded career facts; reading, hiding or muting deletes nothing and does not affect the simulation.'}</p>
    <h3>{cs ? 'Sledované' : 'Followed'}</h3>
    {follows.isPending ? <p role="status">{cs ? 'Načítám…' : 'Loading…'}</p>
      : follows.error ? <p role="alert">{formatApiError(follows.error)}</p>
      : !list ? <p role="alert">{cs ? 'Odpověď neodpovídá tomuto Runu a nebyla zobrazena.' : 'The response does not match this Run and was not displayed.'}</p>
      : list.follows.length === 0 ? <p>{cs ? 'Zatím nic nesledujete.' : 'You follow nothing yet.'}</p>
      : <ul>{list.follows.map(f => <li key={f.kind + f.subject_id}>
        <strong>{f.kind === 'player' ? (cs ? 'Hráč' : 'Player') : (cs ? 'Země' : 'Country')}</strong> {f.subject_id}
        {' · '}{f.alerts_enabled ? (cs ? 'upozornění zapnutá' : 'alerts on') : (cs ? 'upozornění ztišená' : 'alerts muted')}{' '}
        <button type="button" onClick={() => follow.mutate({ kind: f.kind, id: f.subject_id, enabled: !f.alerts_enabled })}>
          {f.alerts_enabled ? (cs ? 'Ztišit' : 'Mute') : (cs ? 'Zapnout' : 'Unmute')}</button>{' '}
        <button type="button" onClick={() => unfollow.mutate({ kind: f.kind, id: f.subject_id })}>
          {cs ? 'Přestat sledovat' : 'Unfollow'}</button></li>)}</ul>}
    <form onSubmit={e => { e.preventDefault(); const id = kind === 'country' ? subject.trim().toUpperCase() : subject.trim(); if (id) { follow.mutate({ kind, id, enabled: true }); setSubject('') } }}>
      <label>{cs ? 'Typ' : 'Type'}{' '}<select value={kind} onChange={e => setKind(e.target.value as 'player' | 'country')}>
        <option value="player">{cs ? 'Hráč' : 'Player'}</option><option value="country">{cs ? 'Země (ISO-3)' : 'Country (ISO-3)'}</option></select></label>{' '}
      <label>{cs ? 'ID hráče / kód země' : 'Player ID / country code'}{' '}
        <input value={subject} onChange={e => setSubject(e.target.value)} /></label>{' '}
      <button type="submit">{cs ? 'Sledovat' : 'Follow'}</button>
    </form>
    {(follow.error || unfollow.error || mark.error) && <p role="alert">{formatApiError(follow.error ?? unfollow.error ?? mark.error)}</p>}
    <h3>{cs ? 'Upozornění' : 'Alerts'}</h3>
    <div data-run-navigation-readonly>
    <label><input type="checkbox" checked={showHidden} onChange={e => url.set({ hidden: e.target.checked ? 'true' : null, page: null })} />{' '}
      {cs ? 'Zobrazit i skrytá' : 'Show hidden too'}</label>
    <div>
      <label>{cs ? 'Hledat hráče nebo zemi' : 'Search player or country'}{' '}
        <input value={url.get('search')} onChange={e => url.set({ search: e.target.value, page: null }, true)} /></label>{' '}
      <label>{cs ? 'Stav karty' : 'Card state'}{' '}
        <select value={stateFilter}
          onChange={e => url.set({ state: e.target.value, page: null })}>
          <option value="all">{cs ? 'Všechny' : 'All'}</option>
          <option value="unread">{cs ? 'Nepřečtené' : 'Unread'}</option>
          <option value="read">{cs ? 'Přečtené' : 'Read'}</option>
          <option value="hidden">{cs ? 'Skryté' : 'Hidden'}</option>
        </select></label>{' '}
      <label>{cs ? 'Druh události v kartě' : 'Event kind in card'}{' '}
        <select value={eventFilter} onChange={e => url.set({ event: e.target.value, page: null })}>
          <option value="all">{cs ? 'Všechny' : 'All'}</option>
          {eventKinds.map(value => <option key={value} value={value}>{(KIND[value] ?? [value, value])[cs ? 0 : 1]}</option>)}
          {eventFilter !== 'all' && !eventKinds.includes(eventFilter) && <option value={eventFilter}>{eventFilter}</option>}
        </select></label>{' '}
      <label>{cs ? 'Chronologicky' : 'Chronological order'}{' '}
        <select value={order === 'asc' ? 'asc' : 'desc'} onChange={e => url.set({ order: e.target.value, page: null })}>
          <option value="desc">{cs ? 'Od nejnovější události' : 'Latest event first'}</option>
          <option value="asc">{cs ? 'Od nejstarší události' : 'Earliest event first'}</option>
        </select></label>{' '}
      <button type="button" onClick={() => url.reset()}>{cs ? 'Reset filtrů' : 'Reset filters'}</button>
    </div>
    </div>
    {follows.isPending || (list !== null && alerts.isPending) ? <p role="status">{cs ? 'Načítám upozornění…' : 'Loading alerts…'}</p>
      : !list ? null
      : alerts.error ? <p role="status">{cs ? 'Upozornění nejsou pro tuto revizi dostupná: ' : 'Alerts are unavailable for this revision: '}{formatApiError(alerts.error)}</p>
      : !cards ? <p role="alert">{cs ? 'Odpověď neodpovídá vybrané Branch nebo uložené revizi a nebyla zobrazena.' : 'The response does not match the selected Branch or Saved revision and was not displayed.'}</p>
      : <>
        <p role="status">{cs ? 'Zobrazené karty' : 'Displayed cards'}: {visible.length}
          {' · '}{cs ? 'Vyhovující filtrům' : 'Matching filters'}: {filtered.length}
          {' · '}{cs ? 'Celkem karet' : 'Total cards'}: {cards.cards.length}
          {' · '}{cs ? 'Nepřečtené podle serveru' : 'Unread reported by server'}: {cards.unread_cards}</p>
        <p><small>{cs ? 'Kritéria pro země jsou prozatímní kalibrace: domácí špička = nejlepší' : 'Country criteria are provisional calibration: domestic leaders = best'} {cards.criteria.domestic_leaders}
          {', '}{cs ? 'mimořádné = ranking' : 'exceptional = rank'} ≤ {cards.criteria.exceptional_rank}.</small></p>
        {cards.cards.length === 0 ? <p>{cs ? 'Žádná upozornění. Fakta zůstávají v kariérní historii hráčů.' : 'No alerts. The facts stay in the players’ career history.'}</p>
          : filtered.length === 0 ? <p>{cs ? 'Žádné karty neodpovídají filtrům.' : 'No cards match these filters.'}</p>
          : <ul>{visible.map(({ value: c }) => <li key={c.notification_key} aria-label={`${c.player_name} ${c.notification_key.slice(0, 8)}`}>
            <strong>{c.player_name}</strong> ({c.country_code}) · {when(c.first_week, cs)}
            {c.first_week.week !== c.last_week.week || c.first_week.season_index !== c.last_week.season_index ? ` → ${when(c.last_week, cs)}` : ''}
            {' · '}{c.item_count} {cs ? 'milníky' : 'milestones'}
            {c.state === 'unread' ? ` · ${cs ? 'nepřečteno' : 'unread'}` : c.state === 'hidden' ? ` · ${cs ? 'skryto' : 'hidden'}` : c.unread_items > 0 ? ` · ${c.unread_items} ${cs ? 'nové' : 'new'}` : ` · ${cs ? 'přečteno' : 'read'}`}
            <br /><small>{c.reasons.map(r => REASON(r, cs)).join('; ')}</small>
            <details><summary>{cs ? 'Podrobnosti a zdroje' : 'Details and sources'}</summary>
              <ul>{c.items.map(i => <li key={i.kind + i.source.fingerprint}>
                {label(i)} · {when(i.effective_week, cs)}{detail(i)}
                <br /><small>{cs ? 'Zdroj' : 'Source'}: {i.source.kind} · {i.source.fingerprint.slice(0, 12)}</small></li>)}</ul></details>
            <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'read', seen: c.item_count })}>{cs ? 'Označit jako přečtené' : 'Mark as read'}</button>{' '}
            {c.state === 'hidden'
              ? <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'unread', seen: c.item_count })}>{cs ? 'Obnovit' : 'Restore'}</button>
              : <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'hidden', seen: c.item_count })}>{cs ? 'Skrýt' : 'Hide'}</button>}
          </li>)}</ul>}
        <nav aria-label={cs ? 'Stránkování upozornění' : 'Alert pagination'}>
          <button type="button" disabled={current <= 1} onClick={() => url.set({ page: String(current - 1) })}>{cs ? 'Předchozí' : 'Previous'}</button>
          {' '}{cs ? 'Strana' : 'Page'} {current} / {pages}{' '}
          <button type="button" disabled={current >= pages} onClick={() => url.set({ page: String(current + 1) })}>{cs ? 'Další' : 'Next'}</button>
        </nav>
      </>}
  </section>
}
