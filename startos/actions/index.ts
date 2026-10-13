import { sdk } from '../sdk'
import { deleteAllData } from './deleteAllData'
import { setAdminPassword } from './setAdminPassword'

export const actions = sdk.Actions.of()
  .addAction(deleteAllData)
  .addAction(setAdminPassword)
