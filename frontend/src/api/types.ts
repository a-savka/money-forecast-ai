import type { components } from './schema'

type S = components['schemas']

export type Category = S['CategoryOut']
export type Account = S['AccountOut']
export type Transaction = S['TransactionOut']
export type TransactionIn = S['TransactionIn']
export type TransactionPatch = S['TransactionPatch']
export type DemoProfile = S['DemoProfile']
export type ImportPreview = S['ImportPreview']
export type ImportResult = S['ImportResult']
export type ColumnMapping = S['ColumnMapping']
export type MockBank = S['MockBankOut']
export type BankConnectResult = S['BankConnectResult']
export type TransactionDraftOut = S['TransactionDraft']
