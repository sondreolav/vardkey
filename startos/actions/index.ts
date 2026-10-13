import { sdk } from '../sdk'
import { deleteHistory } from './deleteHistory'
import { setAdminPassword } from './setAdminPassword'

export const actions = sdk.Actions.of()
  .addAction(deleteHistory)
  .addAction(setAdminPassword)
