type FriendlyErrorProps = {
  message: string;
  onRetry?: () => void;
};

function friendlyMessage(message: string) {
  if (!message) return "";
  if (message.includes("Backend is not running") || message.includes("Failed to fetch")) {
    return "后端服务暂时没有响应。可能是 Render 免费实例正在冷启动，等 30 秒后再试一次。";
  }
  if (message.includes("401") || message.toLowerCase().includes("session")) {
    return "登录状态已经过期。请重新登录后继续。";
  }
  if (message.includes("500")) {
    return "服务器刚才处理失败了。你的数据不会丢，稍后再试一次。";
  }
  if (message.startsWith("{")) {
    try {
      const parsed = JSON.parse(message);
      return parsed.detail || parsed.message || "请求没有成功，请检查输入后再试一次。";
    } catch {
      return "请求没有成功，请检查输入后再试一次。";
    }
  }
  return message;
}

export default function FriendlyError({ message, onRetry }: FriendlyErrorProps) {
  if (!message) return null;

  return (
    <section className="mx-auto max-w-6xl px-5 py-2">
      <div className="rounded-lg border border-red-400/40 bg-red-500/10 p-4 text-red-50">
        <div className="font-semibold">这一步卡住了</div>
        <p className="mt-2 text-sm leading-6 text-red-100">{friendlyMessage(message)}</p>
        <p className="mt-2 text-xs text-red-200/80">原始信息：{message.slice(0, 180)}</p>
        {onRetry ? (
          <button
            className="mt-3 rounded-md border border-red-200/40 px-3 py-2 text-sm font-semibold text-red-50 hover:bg-red-100/10"
            onClick={onRetry}
          >
            Retry
          </button>
        ) : null}
      </div>
    </section>
  );
}
