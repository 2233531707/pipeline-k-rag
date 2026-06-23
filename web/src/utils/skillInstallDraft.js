export const buildSkillDraftConfirmation = (draft, shareConfig, highRiskConfirmed) => {
  const isRemote =
    draft?.source_type === 'remote' ||
    draft?.items?.some((item) => item.source_type === 'remote') === true

  return {
    isRemote,
    canConfirm: !isRemote || highRiskConfirmed === true,
    payload: {
      share_config: shareConfig,
      high_risk_confirmed: isRemote && highRiskConfirmed === true
    }
  }
}
