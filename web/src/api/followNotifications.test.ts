import { describe, expect, it } from 'vitest'
import { validAlertList, validFollowList } from './followNotifications'

const key = 'a'.repeat(64)
const f = 'f'.repeat(64)
const scope = { runId: 'run', branchId: 'branch', savedHead: 'rev-1' }
const item = (patch = {}) => ({
  player_id: 'P1', player_name: 'P', country_code: 'CZE', kind: 'first_recorded_title',
  effective_week: { season_index: 0, week: 10 }, detail: {}, source: { kind: 'played_edition', fingerprint: f },
  reasons: ['player:P1'], ...patch
})
const card = (patch = {}) => ({
  notification_key: key, player_id: 'P1', player_name: 'P', country_code: 'CZE',
  first_week: { season_index: 0, week: 10 }, last_week: { season_index: 0, week: 11 },
  item_count: 1, unread_items: 1, reasons: ['player:P1'], items: [item()], state: 'unread', ...patch
})
const alerts = (cards = [card()], patch = {}) => ({
  schema_version: 'native_tour_notifications.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', as_of_ordinal: 12, unread_cards: 1, cards,
  criteria: { domestic_leaders: 3, exceptional_rank: 1, group_window_weeks: 2, status: 'provisional calibration' }, ...patch
}) as never

describe('follow list contract', () => {
  const list = (follows: unknown[], patch = {}) => ({ schema_version: 'run_follows.v1', run_id: 'run', follows, ...patch }) as never
  it('accepts players and ISO-3 countries and rejects duplicates, bad codes and another Run', () => {
    expect(validFollowList(list([{ kind: 'player', subject_id: 'P1', alerts_enabled: true },
      { kind: 'country', subject_id: 'CZE', alerts_enabled: false }]), 'run')).toBe(true)
    expect(validFollowList(list([{ kind: 'country', subject_id: 'cz', alerts_enabled: true }]), 'run')).toBe(false)
    expect(validFollowList(list([{ kind: 'team', subject_id: 'X', alerts_enabled: true }]), 'run')).toBe(false)
    expect(validFollowList(list([{ kind: 'player', subject_id: 'P1', alerts_enabled: true },
      { kind: 'player', subject_id: 'P1', alerts_enabled: true }]), 'run')).toBe(false)
    expect(validFollowList(list([], { run_id: 'other' }), 'run')).toBe(false)
  })
})

describe('alert list contract', () => {
  it('accepts a grouped card whose items carry their own sources', () => {
    expect(validAlertList(alerts(), scope)).toBe(true)
  })
  it('rejects another Run, Branch or Saved HEAD', () => {
    expect(validAlertList(alerts(undefined, { run_id: 'x' }), scope)).toBe(false)
    expect(validAlertList(alerts(undefined, { branch_id: 'sibling' }), scope)).toBe(false)
    expect(validAlertList(alerts(undefined, { saved_head_revision_id: 'rev-2' }), scope)).toBe(false)
  })
  it('rejects duplicate keys, a card without backing items and a foreign player item', () => {
    expect(validAlertList(alerts([card(), card()]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ items: [], item_count: 0 })]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ item_count: 2 })]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ items: [item({ player_id: 'P2' })] })]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ items: [item({ source: { kind: 'x', fingerprint: '' } })] })]), scope)).toBe(false)
  })
  it('rejects impossible unread counts, states and keys', () => {
    expect(validAlertList(alerts([card({ unread_items: 2 })]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ state: 'deleted' })]), scope)).toBe(false)
    expect(validAlertList(alerts([card({ notification_key: 'short' })]), scope)).toBe(false)
  })
})
