// Vercel Serverless Function entry point for CryptoShift API
import { handleRequest } from "../backend/src/server.js";

export default async function handler(req, res) {
  return handleRequest(req, res);
}

