import fs from "node:fs";
import path from "node:path";
import { ethers } from "ethers";
import solc from "solc";

const rpcUrl = process.env.EVM_RPC_URL ?? "http://ganache:8545";
const artifactPath =
  process.env.EVM_ARTIFACT_PATH ?? "/shared/SentinelLedger.json";
const sourcePath = path.resolve("contracts/SentinelLedger.sol");

async function waitForRpc() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(rpcUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "eth_chainId",
          params: [],
        }),
      });
      if (response.ok) return;
    } catch {
      // Ganache is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Ganache did not become available at ${rpcUrl}`);
}

function compile() {
  const input = {
    language: "Solidity",
    sources: {
      "SentinelLedger.sol": {
        content: fs.readFileSync(sourcePath, "utf8"),
      },
    },
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
      evmVersion: "shanghai",
      outputSelection: {
        "*": { "*": ["abi", "evm.bytecode.object"] },
      },
    },
  };
  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  const errors = (output.errors ?? []).filter(
    (item) => item.severity === "error",
  );
  if (errors.length) {
    throw new Error(errors.map((item) => item.formattedMessage).join("\n"));
  }
  return output.contracts["SentinelLedger.sol"].SentinelLedger;
}

await waitForRpc();
const provider = new ethers.JsonRpcProvider(rpcUrl);
if (fs.existsSync(artifactPath)) {
  const existing = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const code = await provider.getCode(existing.address);
  if (code !== "0x") {
    console.log(`SentinelLedger already deployed at ${existing.address}`);
    process.exit(0);
  }
}
const signers = await Promise.all([0, 1, 2].map((index) => provider.getSigner(index)));
const accounts = await Promise.all(signers.map((signer) => signer.getAddress()));
const compiled = compile();
const factory = new ethers.ContractFactory(
  compiled.abi,
  `0x${compiled.evm.bytecode.object}`,
  signers[0],
);
const contract = await factory.deploy(accounts, ["gulf", "atlas", "orion"], 100);
await contract.waitForDeployment();

const artifact = {
  address: await contract.getAddress(),
  abi: compiled.abi,
  chainId: Number((await provider.getNetwork()).chainId),
  companies: {
    gulf: accounts[0],
    atlas: accounts[1],
    orion: accounts[2],
  },
};
fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2));
console.log(`SentinelLedger deployed at ${artifact.address}`);
