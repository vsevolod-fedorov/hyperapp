import traceback

from .code.mark import mark


@mark.service
def error_view(view_reg, visualizer, exception, ctx):
    tb_lines = traceback.format_exception(exception)
    model = str(exception) + '\n\n' + ''.join(tb_lines)
    view_piece = visualizer(model)
    model_ctx = ctx.clone_with(model=model)
    return (model, model_ctx, view_piece)
