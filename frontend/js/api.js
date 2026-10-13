/* ============================================================
 * api.js — 统一 API 请求模块（全站唯一 fetch 入口）
 * ------------------------------------------------------------
 * 代码规范：任何页面禁止直接使用 fetch，只能通过
 *   API.get(url, params)  /  API.post(url, data)
 *   API.put(url, data)    /  API.delete(url)
 * 统一响应格式（与后端 utils/response.py 一致）：
 *   成功: {code: 200, message: "success", data: {...}}
 *   失败: {code: 4xx/5xx, message: "错误信息", data: null}
 * 本模块对页面只暴露 data 部分；失败抛出 ApiError（携带 message/code/data）。
 * ============================================================ */

/** 业务错误对象：message=后端提示文案，data=附加数据（如库存不足的 available/required） */
function ApiError(message, code, data) {
  var err = new Error(message);
  err.name = "ApiError";
  err.code = code;
  err.data = data;
  return err;
}

/** 拼接查询参数（自动忽略空值） */
function buildQuery(params) {
  var parts = [];
  Object.keys(params || {}).forEach(function (key) {
    var v = params[key];
    if (v === null || v === undefined || v === "") return;
    parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(v));
  });
  return parts.length ? "?" + parts.join("&") : "";
}

var API = {
  /** 底层请求（统一处理 JSON 包装与错误，页面不要直接调用） */
  request: function (method, url, data) {
    var options = {
      method: method,
      headers: { "Content-Type": "application/json" },
    };

    // TODO-EXTENSION: 接入登录认证后，在此统一附带 token
    // var token = localStorage.getItem("erp_token");
    // if (token) options.headers["Authorization"] = "Bearer " + token;

    if (data !== undefined && data !== null) {
      options.body = JSON.stringify(data);
    }

    return fetch(APP_CONFIG.API_BASE_URL + url, options)
      .catch(function () {
        // 网络层失败：后端未启动 / 跨域被拦
        throw new ApiError(
          "无法连接后端服务，请确认已运行 python backend/app.py（127.0.0.1:5000）",
          0, null
        );
      })
      .then(function (res) {
        return res.json().catch(function () {
          throw new ApiError("后端返回数据格式错误（HTTP " + res.status + "）", res.status, null);
        });
      })
      .then(function (json) {
        if (json.code !== 200) {
          throw new ApiError(json.message || "请求失败", json.code, json.data === undefined ? null : json.data);
        }
        return json.data;
      });
  },

  /** GET 查询 */
  get: function (url, params) {
    return API.request("GET", url + buildQuery(params));
  },

  /** POST 新增 / 触发动作 */
  post: function (url, data) {
    return API.request("POST", url, data || {});
  },

  /** PUT 修改 */
  put: function (url, data) {
    return API.request("PUT", url, data || {});
  },

  /** DELETE 删除 */
  delete: function (url) {
    return API.request("DELETE", url);
  },
};
