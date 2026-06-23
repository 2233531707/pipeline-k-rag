export const DEFAULT_KNOWLEDGE_GROUP_ID = 'default'

export function buildKnowledgeGroupSections(groups = [], databases = []) {
  const normalizedGroups = [...groups]
  if (!normalizedGroups.some((group) => group.group_id === DEFAULT_KNOWLEDGE_GROUP_ID)) {
    normalizedGroups.unshift({
      group_id: DEFAULT_KNOWLEDGE_GROUP_ID,
      name: '默认分组',
      is_default: true
    })
  }

  const sections = normalizedGroups
    .sort((a, b) => {
      if (a.is_default) return -1
      if (b.is_default) return 1
      return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
    })
    .map((group) => ({
      ...group,
      parent_group_id: group.parent_group_id || null,
      children: [],
      databases: []
    }))

  const sectionById = new Map(sections.map((section) => [section.group_id, section]))
  const defaultSection = sectionById.get(DEFAULT_KNOWLEDGE_GROUP_ID)

  for (const section of sections) {
    if (!section.parent_group_id) continue
    const parent = sectionById.get(section.parent_group_id)
    if (!parent || parent.group_id === section.group_id) {
      section.parent_group_id = null
      continue
    }
    parent.children.push(section)
  }

  for (const database of databases) {
    const section = sectionById.get(database.group_id || DEFAULT_KNOWLEDGE_GROUP_ID) || defaultSection
    section.databases.push(database)
  }

  return sections.filter((section) => !section.parent_group_id)
}
