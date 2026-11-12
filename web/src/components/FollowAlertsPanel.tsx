import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  deleteRunFollow, getFollowAlerts, getRunFollows, putAlertState, putRunFollow
} from '../api/client'
import { validAlertList, validFollowList } from '../api/followNotifications'
import type { AlertItem } from '../api/followNotifications'
import { formatApiError } from '../utils/apiErrors'

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
  const [showHidden, setShowHidden] = useState(false)
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
    mutationFn: (v: { key: string; state: 'unread' | 'read' | 'hidden' }) => putAlertState(runId, branchId, v.key, v.state),
    onSuccess: refresh
  })
  const title = cs ? 'Sledování a upozornění' : 'Following and alerts'
  const cards = alerts.data && validAlertList(alerts.data, { runId, branchId, savedHead }) ? alerts.data : null
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
    <label><input type="checkbox" checked={showHidden} onChange={e => setShowHidden(e.target.checked)} />{' '}
      {cs ? 'Zobrazit i skrytá' : 'Show hidden too'}</label>
    {follows.isPending || (list !== null && alerts.isPending) ? <p role="status">{cs ? 'Načítám upozornění…' : 'Loading alerts…'}</p>
      : !list ? null
      : alerts.error ? <p role="status">{cs ? 'Upozornění nejsou pro tuto revizi dostupná: ' : 'Alerts are unavailable for this revision: '}{formatApiError(alerts.error)}</p>
      : !cards ? <p role="alert">{cs ? 'Odpověď neodpovídá vybrané Branch nebo uložené revizi a nebyla zobrazena.' : 'The response does not match the selected Branch or Saved revision and was not displayed.'}</p>
      : <>
        <p role="status">{cs ? 'Nepřečtených karet' : 'Unread cards'}: {cards.unread_cards}</p>
        <p><small>{cs ? 'Kritéria pro země jsou prozatímní kalibrace: domácí špička = nejlepší' : 'Country criteria are provisional calibration: domestic leaders = best'} {cards.criteria.domestic_leaders}
          {', '}{cs ? 'mimořádné = ranking' : 'exceptional = rank'} ≤ {cards.criteria.exceptional_rank}.</small></p>
        {cards.cards.length === 0 ? <p>{cs ? 'Žádná upozornění. Fakta zůstávají v kariérní historii hráčů.' : 'No alerts. The facts stay in the players’ career history.'}</p>
          : <ul>{cards.cards.map(c => <li key={c.notification_key} aria-label={`${c.player_name} ${c.notification_key.slice(0, 8)}`}>
            <strong>{c.player_name}</strong> ({c.country_code}) · {when(c.first_week, cs)}
            {c.first_week.week !== c.last_week.week || c.first_week.season_index !== c.last_week.season_index ? ` → ${when(c.last_week, cs)}` : ''}
            {' · '}{c.item_count} {cs ? 'milníky' : 'milestones'}
            {c.state === 'unread' ? ` · ${cs ? 'nepřečteno' : 'unread'}` : c.state === 'hidden' ? ` · ${cs ? 'skryto' : 'hidden'}` : c.unread_items > 0 ? ` · ${c.unread_items} ${cs ? 'nové' : 'new'}` : ` · ${cs ? 'přečteno' : 'read'}`}
            <br /><small>{c.reasons.map(r => REASON(r, cs)).join('; ')}</small>
            <details><summary>{cs ? 'Podrobnosti a zdroje' : 'Details and sources'}</summary>
              <ul>{c.items.map(i => <li key={i.kind + i.source.fingerprint}>
                {label(i)} · {when(i.effective_week, cs)}{detail(i)}
                <br /><small>{cs ? 'Zdroj' : 'Source'}: {i.source.kind} · {i.source.fingerprint.slice(0, 12)}</small></li>)}</ul></details>
            <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'read' })}>{cs ? 'Označit jako přečtené' : 'Mark as read'}</button>{' '}
            {c.state === 'hidden'
              ? <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'unread' })}>{cs ? 'Obnovit' : 'Restore'}</button>
              : <button type="button" onClick={() => mark.mutate({ key: c.notification_key, state: 'hidden' })}>{cs ? 'Skrýt' : 'Hide'}</button>}
          </li>)}</ul>}
      </>}
  </section>
}
