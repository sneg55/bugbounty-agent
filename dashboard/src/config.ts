import { ethers } from 'ethers'

export const RPC_URL = 'https://sepolia.base.org'
export const CHAIN_ID = 84532

export function getProvider() {
  return new ethers.JsonRpcProvider(RPC_URL)
}
