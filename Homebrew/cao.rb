class Cao < Formula
  include Language::Python::Virtualenv

  desc "一个捕获终端错误并使用 AI 分析的命令行工具"
  homepage "https://github.com/zhouatie/cao"
  url "https://github.com/zhouatie/cao/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "e21c7e8969cf06e7a3b6a2a6edbb85ef9e19a85321841cd120e0208e640d3ed9"
  license "MIT"

  depends_on "python@3.10"

  resource "requests" do
    url "https://files.pythonhosted.org/packages/9d/be/10918a2eac4ae9f02f6cfe6414b7a155ccd8f7f9d4380d62fd5b955065c3/requests-2.31.0.tar.gz"
    sha256 "942c5a758f98d790eaed1a29cb6eefc7ffb0d1cf7af05c3d2791656dbd6ad1e1"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "cao", shell_output("#{bin}/cao --help")
  end
end
