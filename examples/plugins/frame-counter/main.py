"""frame-counter：演示插件钩子 on_boot / on_frame / on_stop。"""

_booted_at = None


def on_boot(ctx):
    global _booted_at
    import time

    _booted_at = time.time()
    ctx.state["frames"] = 0
    ctx.log(f"frame-counter 启动于实例 {ctx.instance_name}")


def on_frame(ctx, vm):
    ctx.state["frames"] = ctx.state.get("frames", 0) + 1
    # 示例：统计亮屏比例（每 60 帧记录一次）
    if ctx.state["frames"] % 60 == 0 and hasattr(vm, "lit_ratio"):
        ctx.log(f"frame {ctx.state['frames']}，亮屏 {vm.lit_ratio():.1%}")


def on_stop(ctx):
    ctx.log(f"frame-counter 结束，共 {ctx.state.get('frames', 0)} 帧")
