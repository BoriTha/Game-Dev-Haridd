# Level Generation System Flow Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph "Game Loop"
        GL[Game Loop in main.py]
        LC[Level Class]
        TS[Terrain System]
        ES[Enemy System]
    end
    
    subgraph "Level Generation System"
        SM[Seed Manager]
        GC[Generation Config]
        LG[Level Generator]
        LV[Level Validator]
        TG[Terrain Generator]
        EP[Entity Placer]
    end
    
    subgraph "Generation Algorithms"
        BSP[BSP Generator]
        CA[Cellular Automata]
        PN[Perlin Noise]
        WFC[Wave Function Collapse]
    end
    
    GL --> LC
    LC --> TS
    LC --> ES
    
    GL -.-> |"Request New Level"| SM
    SM --> |"Seed Data"| LG
    GC --> |"Parameters"| LG
    
    LG --> |"Raw Level Data"| LV
    LV --> |"Validated Level"| LC
    
    LG --> TG
    LG --> EP
    
    TG --> |"Terrain Grid"| LC
    EP --> |"Enemy/Item Placements"| LC
    
    LG --> BSP
    LG --> CA
    LG --> PN
    LG --> WFC
```

## Generation Pipeline Flow

```mermaid
flowchart TD
    Start([Start Generation]) --> GetSeed[Get/Generate Seed]
    GetSeed --> GetConfig[Load Generation Config]
    GetConfig --> SelectAlgo[Select Algorithm Based on Level Type]
    
    SelectAlgo --> BSP_Branch{BSP Algorithm?}
    SelectAlgo --> CA_Branch{Cellular Automata?}
    SelectAlgo --> PN_Branch{Perlin Noise?}
    SelectAlgo --> WFC_Branch{WFC Algorithm?}
    
    BSP_Branch -->|Yes| BSP_Gen[Generate BSP Structure]
    CA_Branch -->|Yes| CA_Gen[Generate Cave Structure]
    PN_Branch -->|Yes| PN_Gen[Generate Noise-based Structure]
    WFC_Branch -->|Yes| WFC_Gen[Generate WFC Structure]
    
    BSP_Gen --> GenerateTerrain[Generate Terrain]
    CA_Gen --> GenerateTerrain
    PN_Gen --> GenerateTerrain
    WFC_Gen --> GenerateTerrain
    
    GenerateTerrain --> PlaceEntities[Place Enemies and Items]
    PlaceEntities --> ValidateLevel[Validate Playability]
    
    ValidateLevel --> ValidCheck{Level Valid?}
    ValidCheck -->|Yes| Finalize[Finalize Level]
    ValidCheck -->|No| RepairAttempt{Repair Attempts < Max?}
    
    RepairAttempt -->|Yes| RepairLevel[Repair Level Issues]
    RepairAttempt -->|No| Regenerate[Regenerate with New Seed]
    
    RepairLevel --> ValidateLevel
    Regenerate --> GetSeed
    
    Finalize --> LoadLevel[Load into Game]
    LoadLevel --> End([Generation Complete])
```

## Terrain Integration Flow

```mermaid
graph LR
    subgraph "Existing Terrain System"
        TT[TerrainType Enum]
        TP[TerrainProperties]
        TSL[TerrainSystem Logic]
    end
    
    subgraph "New Generation Components"
        TGen[Terrain Generator]
        TR[Terrain Rules]
        TV[Terrain Validation]
    end
    
    TGen --> |"Uses"| TT
    TGen --> |"Applies"| TR
    TGen --> |"Validates with"| TV
    
    TV --> |"Integrates with"| TP
    TV --> |"Uses existing"| TSL
    
    TGen --> |"Produces"| TG[Terrain Grid]
    TG --> |"Loaded by"| LC[Level Class]
```

## Entity Placement Flow

```mermaid
flowchart TD
    StartEntity([Entity Placement Start]) --> GetTerrain[Get Terrain Data]
    GetTerrain --> SelectEnemies[Select Enemy Types]
    SelectEnemies --> GetTraits[Get Enemy Terrain Traits]
    
    GetTraits --> FindValid[Find Valid Positions]
    FindValid --> FilterTerrain[Filter by Terrain Compatibility]
    FilterTerrain --> CheckVision[Check Vision Requirements]
    CheckVision --> ValidateSpace[Validate Combat Space]
    
    ValidateSpace --> PlaceEnemy[Place Enemy]
    PlaceEnemy --> MoreEnemies{More Enemies?}
    
    MoreEnemies -->|Yes| GetTraits
    MoreEnemies -->|No| PlaceItems[Place Items and Features]
    
    PlaceItems --> ValidatePlacement[Validate All Placements]
    ValidatePlacement --> ValidPlacement{All Valid?}
    
    ValidPlacement -->|Yes| DoneEntity[Placement Complete]
    ValidPlacement -->|No| Rebalance[Rebalance Placements]
    
    Rebalance --> FindValid
```

## Seed Management Flow

```mermaid
stateDiagram-v2
    [*] --> GenerateWorldSeed
    GenerateWorldSeed --> GenerateLevelSeed
    GenerateLevelSeed --> GenerateSubSeeds
    GenerateSubSeeds --> StructureSeed
    GenerateSubSeeds --> TerrainSeed
    GenerateSubSeeds --> EnemySeed
    GenerateSubSeeds --> ItemSeed
    
    StructureSeed --> GenerateStructure
    TerrainSeed --> GenerateTerrain
    EnemySeed --> PlaceEnemies
    ItemSeed --> PlaceItems
    
    GenerateStructure --> ValidateLevel
    GenerateTerrain --> ValidateLevel
    PlaceEnemies --> ValidateLevel
    PlaceItems --> ValidateLevel
    
    ValidateLevel --> LevelValid: Valid
    ValidateLevel --> LevelInvalid: Invalid
    
    LevelValid --> NextLevel
    LevelInvalid --> RegenerateLevel
    
    RegenerateLevel --> GenerateLevelSeed
    NextLevel --> GenerateLevelSeed
```

## Validation System Flow

```mermaid
flowchart TD
    StartVal([Validation Start]) --> StructVal[Structural Validation]
    
    StructVal --> Connectivity[Check Connectivity]
    Connectivity --> Boundaries[Validate Boundaries]
    Boundaries --> Exits[Check Exit Placement]
    
    Exits --> GameVal[Gameplay Validation]
    GameVal --> EnemyReach[Check Enemy Reachability]
    EnemyReach --> CombatSpace[Validate Combat Space]
    CombatSpace --> TerrainNav[Check Terrain Navigation]
    TerrainNav --> Difficulty[Validate Difficulty Balance]
    
    Difficulty --> ValidationResult{All Checks Pass?}
    
    ValidationResult -->|Yes| ValidLevel[Level is Valid]
    ValidationResult -->|No| IdentifyIssues[Identify Issues]
    
    IdentifyIssues --> CanRepair{Can Auto-Repair?}
    CanRepair -->|Yes| AutoRepair[Apply Auto-Repair]
    CanRepair -->|No| ManualFix[Requires Manual Fix]
    
    AutoRepair --> Revalidate[Revalidate Repaired Level]
    ManualFix --> Fail[Generation Failed]
    
    Revalidate --> ValidationResult
    ValidLevel --> Success[Validation Success]
```

## Integration Points with Existing Code

```mermaid
graph TB
    subgraph "Current System"
        L1[level.py - Level Class]
        M1[main.py - Game Loop]
        T1[terrain_system.py - Terrain System]
        E1[enemy_entities.py - Enemy Classes]
        C1[config.py - Configuration]
    end
    
    subgraph "New System"
        L2[level_generation/generator.py]
        S2[level_generation/seed_manager.py]
        V2[level_generation/validators.py]
        T2[level_generation/terrain_generator.py]
        E2[level_generation/entity_placer.py]
        G2[level_generation/config/generation_config.py]
    end
    
    L1 -.-> |"Replaced by"| L2
    M1 -.-> |"Modified to use"| L2
    T1 -.-> |"Enhanced by"| T2
    E1 -.-> |"Used by"| E2
    C1 -.-> |"Extended by"| G2
    
    L2 --> S2
    L2 --> V2
    L2 --> T2
    L2 --> E2
    L2 --> G2
```

## Performance Considerations

```mermaid
graph LR
    subgraph "Generation Performance"
        GT[Generation Time < 100ms]
        VS[Validation Success Rate > 95%]
        MC[Memory Usage < 50MB]
        CR[Cache Reuse Rate > 80%]
    end
    
    subgraph "Optimization Strategies"
        LG[Lazy Generation]
        CC[Component Caching]
        PP[Parallel Processing]
        MM[Memory Management]
    end
    
    GT --> LG
    VS --> CC
    MC --> MM
    CR --> PP
```

## Migration Timeline

```mermaid
gantt
    title Level Generation Migration Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation
    Seed Manager        :p1-1, 2024-01-01, 7d
    Basic Generator      :p1-2, after p1-1, 7d
    Level Integration    :p1-3, after p1-2, 7d
    
    section Phase 2: Core Generation
    Terrain System       :p2-1, after p1-3, 7d
    Entity Placement     :p2-2, after p2-1, 7d
    Validation Pipeline  :p2-3, after p2-2, 7d
    
    section Phase 3: Advanced Features
    Multiple Algorithms  :p3-1, after p2-3, 7d
    Difficulty Scaling   :p3-2, after p3-1, 7d
    Special Features     :p3-3, after p3-2, 7d
    
    section Phase 4: Polish
    Testing & Balancing :p4-1, after p3-3, 14d
    Optimization        :p4-2, after p4-1, 7d
    Documentation       :p4-3, after p4-2, 7d