"use strict";

const { contextBridge } = require("electron");

const BACKEND_URL = "http://127.0.0.1:8000";

contextBridge.exposeInMainWorld("electronAPI", {
  backendUrl: BACKEND_URL,
});
