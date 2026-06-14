export type Transaction = {
  id: string;
  type: string;
  sender: string;
  recipient: string;
  amount: number;
  timestamp: string;
  payload: Record<string, unknown>;
  signature: string;
  public_key: string;
};

export type Block = {
  index: number;
  timestamp: string;
  previous_hash: string;
  hash: string;
  nonce: number;
  transactions: Transaction[];
  node_id: string;
};

export type Company = {
  company_id: string;
  name: string;
  wallet_address: string;
  balance: number;
};

export type AuthCompany = Company & {
  expires_at?: number;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: number;
  company: AuthCompany;
};

export type MissionDetails = {
  report: {
    mission_id: string;
    company_id: string;
    company_wallet_address: string;
    drone_id: string;
    route_id: string;
    detailed_route: string;
    result: string;
    description: string;
    evidence: string[];
    strategic_notes: string;
    risk_classification: string;
    timestamp: string;
  };
  calculated_hash: string;
  registered_hash: string;
  valid: boolean;
};

export type Wallet = Company & {
  public_key: string;
  encryption_public_key: string;
};

export type Drone = {
  drone_id: string;
  available: boolean;
  active_mission?: string;
};

export type Mission = {
  mission_id: string;
  company_id: string;
  company_wallet_address: string;
  drone_id: string;
  route_id: string;
  status: string;
  result?: string;
  created_at: string;
  completed_at?: string;
  storage_pointer?: string;
  report_hash?: string;
  encrypted_file_hash?: string;
  cost: number;
};

export type NodeStatus = {
  node_id: string;
  online: boolean;
  height: number;
  transactions: number;
  mempool: number;
  peers: number;
  chain_valid: boolean;
  url?: string;
};
