export const clearDesktopSubagentThreadModalState = (modalState) => {
  if (!modalState) return

  modalState.open = false
  modalState.childThreadId = ''
  modalState.subagentName = ''
  modalState.subagentAvatar = ''
}
