import assert from 'node:assert/strict'

import { clearDesktopSubagentThreadModalState } from '../desktopChatState.js'

const run = () => {
  const modalState = {
    open: true,
    childThreadId: 'child-thread-1',
    subagentName: 'research-explorer',
    subagentAvatar: 'https://backend.example.com/avatar.png'
  }

  clearDesktopSubagentThreadModalState(modalState)

  assert.deepEqual(modalState, {
    open: false,
    childThreadId: '',
    subagentName: '',
    subagentAvatar: ''
  })

  console.log('desktopChatState: all assertions passed')
}

run()
