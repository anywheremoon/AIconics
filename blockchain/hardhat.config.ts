import { defineConfig } from "hardhat/config";

export default defineConfig({
  solidity: "0.8.24",
  networks: {
    localhost: {
      type: "http",
      chainType: "l1",
      url: "http://127.0.0.1:8545",
    },
  },
});
