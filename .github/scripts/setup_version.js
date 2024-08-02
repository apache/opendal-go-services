const semver = require('semver')

const getLatestTag = async (github, owner, repo, tag_format) => {
  const { status, data } = await github.rest.git.listMatchingRefs({
    owner,
    repo,
    ref: `tags/${tag_format}`,
  })
  if (status != 200) {
    throw new Error(`Failed to fetch tags for ${owner}/${repo}`)
  }
  const tags = data.map((ref) => {
    const version = ref.ref.replace(`refs/tags/${tag_format}`, '')
    return version
  })
  if (tags.length === 0) {
    return '0.0.0'
  }
  max_version = tags.reduce((a, b) => semver.gt(a, b) ? a : b) ?? '0.0.0'
  return max_version
}


module.exports = async ({ github }) => {
  const bindingTag = await getLatestTag(github, 'apache', 'opendal', 'bindings/go/v')
  const serviceTag = await getLatestTag(github, 'apache', 'opendal-go-services', 'v')

  const opendalGoVersion = semver.gt(bindingTag, serviceTag) ? `v${bindingTag}` : ''
  const opendalCoreVersion = `v${await getLatestTag(github, "apache", "opendal", "v")}`

  console.log(`opendal_core_version=${opendalCoreVersion}`)
  console.log(`opendal_go_version=${opendalGoVersion}`)

  const fs = require('fs')
  const output = process.env.GITHUB_OUTPUT

  fs.appendFileSync(output, `opendal_core_version=${opendalCoreVersion}\n`)
  fs.appendFileSync(output, `opendal_go_version=${opendalGoVersion}\n`)
}

