// Conventional Commits — mesmo padrão já usado nos commits deste repo
// (feat:, fix:, chore:, docs: ...). Gratuito, roda só localmente via
// o hook commit-msg do Husky.
module.exports = {
  extends: ["@commitlint/config-conventional"],
};
