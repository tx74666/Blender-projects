# 插件维护位置

RR Helper 和 Character Designer 已集中到：

`D:\MyRepository\Blender-addons-by-Randy\addons`

后续插件开发以该仓库为入口，安装包位于该仓库的 `dist/`。
本目录是 Character Designer 的项目验证副本，供 X 的既有场景测试使用。
从共享仓库运行 `tools/deploy_local.py --project-addons D:\Blender\Projects\Character\X\addons`
更新本目录，并加 `--check` 校验一致性；不要先修改本目录再回抄源码。
角色模型与真实场景验证继续留在 X 项目中。
