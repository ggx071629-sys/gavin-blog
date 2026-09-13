export function slugify(value: string): string {
  return value
    .normalize('NFKD')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
}

export interface ArticleCreateFieldErrors {
  title: string
  slug: string
}

const ARTICLE_SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export function validateArticleCreateFields(input: { title: string, slug: string }): ArticleCreateFieldErrors {
  const title = input.title.trim()
  const slug = input.slug.trim()
  const errors: ArticleCreateFieldErrors = { title: '', slug: '' }

  if (!title) errors.title = '请输入文章标题。'
  if (!slug) {
    errors.slug = title && !slugify(title)
      ? '当前标题无法自动生成 Slug，请填写英文或拼音 Slug。'
      : '请输入 Slug。'
  }
  else if (slug.length > 160 || !ARTICLE_SLUG_PATTERN.test(slug)) {
    errors.slug = 'Slug 只能使用小写英文字母、数字和单个连字符，且不能以连字符开头或结尾。'
  }

  return errors
}
