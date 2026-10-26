import type { components } from './schema'

type S = components['schemas']

export type Category = S['CategoryOut']
export type Account = S['AccountOut']
export type Transaction = S['TransactionOut']
export type TransactionIn = S['TransactionIn']
export type TransactionPatch = S['TransactionPatch']
export type DemoProfile = S['DemoProfile']
