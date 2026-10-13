import { sdk } from '../sdk'
import { deleteHistory } from './deleteHistory'

export const actions = sdk.Actions.of().addAction(deleteHistory)
