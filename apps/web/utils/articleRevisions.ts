export const REVISION_SOURCE_LABELS: Record<string, string> = {
  editor: '编辑器发布',
  incubator: '历史孵化发布',
  rollback: '版本回滚',
}

const REVISION_ERROR_LABELS: Record<string, string> = {
  ARTICLE_VERSION_CONFLICT: '文章版本已被其他操作更新',
  ARTICLE_WORKING_COPY_DIRTY: '目标文章存在未发布修改',
  PUBLISH_NOT_ELIGIBLE: '当前文章不满足发布或回滚条件',
  REVISION_NOT_FOUND: '文章修订不存在',
}

export function revisionErrorLabel(code: string | null | undefined): string {
  return code ? (REVISION_ERROR_LABELS[code] ?? code) : ''
}
