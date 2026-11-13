export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers:
      options.body && !(options.body instanceof FormData)
        ? { "Content-Type": "application/json", ...options.headers }
        : options.headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again."
    );
  }
  return data;
}

const TOOL_LABELS = {
  calculator: "Calculator",
  mcp_calculator: "Calculator",
  search_knowledge_base: "Course search",
  mcp_search_knowledge_base: "Course search",
};

export function toolLabel(name) {
  return TOOL_LABELS[name] || name || "Tool";
}