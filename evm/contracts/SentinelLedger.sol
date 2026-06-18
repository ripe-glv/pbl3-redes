// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SentinelLedger {
    struct Mission {
        string missionId;
        address company;
        string companyId;
        string droneId;
        string routeId;
        uint256 cost;
        uint256 createdAt;
        bool completed;
        string result;
        string riskClassification;
        string storagePointer;
        string reportHash;
        string encryptedFileHash;
        string encryptedAccessKey;
    }

    address public immutable administrator;
    mapping(address => uint256) public credits;
    mapping(address => string) public companyIds;
    mapping(string => address) public companyAddresses;
    mapping(string => bool) public droneBusy;
    mapping(string => string) public droneMission;
    mapping(string => Mission) private missions;
    string[] private missionIds;

    event GenesisCredit(address indexed company, string companyId, uint256 amount);
    event CreditTransferred(
        address indexed sender,
        address indexed recipient,
        uint256 amount
    );
    event EscortRequested(
        string missionId,
        address indexed company,
        string companyId,
        string droneId,
        string routeId,
        uint256 cost
    );
    event MissionCompleted(
        string missionId,
        address indexed company,
        string result,
        string reportHash,
        string encryptedFileHash
    );

    constructor(
        address[] memory initialCompanies,
        string[] memory initialCompanyIds,
        uint256 initialCredit
    ) {
        require(
            initialCompanies.length == initialCompanyIds.length,
            "Invalid company configuration"
        );
        administrator = msg.sender;
        for (uint256 i = 0; i < initialCompanies.length; i++) {
            address account = initialCompanies[i];
            string memory companyId = initialCompanyIds[i];
            require(account != address(0), "Invalid company account");
            require(bytes(companyIds[account]).length == 0, "Duplicate account");
            companyIds[account] = companyId;
            companyAddresses[companyId] = account;
            credits[account] = initialCredit;
            emit GenesisCredit(account, companyId, initialCredit);
        }
    }

    modifier onlyCompany() {
        require(bytes(companyIds[msg.sender]).length != 0, "Unknown company");
        _;
    }

    function transferCredits(
        address recipient,
        uint256 amount
    ) external onlyCompany {
        require(recipient != msg.sender, "Same sender and recipient");
        require(bytes(companyIds[recipient]).length != 0, "Unknown recipient");
        require(amount > 0, "Amount must be positive");
        require(credits[msg.sender] >= amount, "Insufficient credits");
        credits[msg.sender] -= amount;
        credits[recipient] += amount;
        emit CreditTransferred(msg.sender, recipient, amount);
    }

    function requestEscort(
        string calldata missionId,
        string calldata droneId,
        string calldata routeId,
        uint256 cost
    ) external onlyCompany {
        require(bytes(missions[missionId].missionId).length == 0, "Mission exists");
        require(!droneBusy[droneId], "Drone unavailable");
        require(cost > 0, "Cost must be positive");
        require(credits[msg.sender] >= cost, "Insufficient credits");

        credits[msg.sender] -= cost;
        droneBusy[droneId] = true;
        droneMission[droneId] = missionId;
        missions[missionId] = Mission({
            missionId: missionId,
            company: msg.sender,
            companyId: companyIds[msg.sender],
            droneId: droneId,
            routeId: routeId,
            cost: cost,
            createdAt: block.timestamp,
            completed: false,
            result: "",
            riskClassification: "",
            storagePointer: "",
            reportHash: "",
            encryptedFileHash: "",
            encryptedAccessKey: ""
        });
        missionIds.push(missionId);
        emit EscortRequested(
            missionId,
            msg.sender,
            companyIds[msg.sender],
            droneId,
            routeId,
            cost
        );
    }

    function completeMission(
        string calldata missionId,
        string calldata result,
        string calldata riskClassification,
        string calldata storagePointer,
        string calldata reportHash,
        string calldata encryptedFileHash,
        string calldata encryptedAccessKey
    ) external onlyCompany {
        Mission storage mission = missions[missionId];
        require(bytes(mission.missionId).length != 0, "Mission not found");
        require(mission.company == msg.sender, "Not mission owner");
        require(!mission.completed, "Mission already completed");

        mission.completed = true;
        mission.result = result;
        mission.riskClassification = riskClassification;
        mission.storagePointer = storagePointer;
        mission.reportHash = reportHash;
        mission.encryptedFileHash = encryptedFileHash;
        mission.encryptedAccessKey = encryptedAccessKey;
        droneBusy[mission.droneId] = false;
        droneMission[mission.droneId] = "";

        emit MissionCompleted(
            missionId,
            msg.sender,
            result,
            reportHash,
            encryptedFileHash
        );
    }

    function getMission(string calldata missionId) external view returns (Mission memory) {
        require(bytes(missions[missionId].missionId).length != 0, "Mission not found");
        return missions[missionId];
    }

    function getMissionCount() external view returns (uint256) {
        return missionIds.length;
    }

    function getMissionId(uint256 index) external view returns (string memory) {
        return missionIds[index];
    }
}
