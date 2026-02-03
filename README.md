# Lods-mTI: RFID Missing Tag Identification with High-Fidelity Simulation

[English](#english) | [简体中文](#简体中文)

---

## English

### Overview
**Lods-mTI** (Loss-tolerant Open-loop Detection System for Missing Tag Identification) is a high-performance research framework designed for Large-scale RFID systems. It focuses on identifying missing tags in the presence of physical layer impairments such as noise, clock drift, and burst erasure.

The core of this repository is the **Lods-mTI algorithm**, which utilizes an adaptive tree-based open-loop architecture and a voting mechanism to achieve high reliability and throughput in complex environments.

### Key Features
- **High-Fidelity Physics Kernel**: A universal simulation engine supporting BER, clock drift, burst erasure, capture effect, and energy tracking.
- **Adaptive Voting Mechanism**: Dynamic adjustment of verification density ($\rho$) based on environmental noise levels.
- **Comprehensive Baselines**: Includes implementations of state-of-the-art algorithms: CR-MTI, ECUMI, CTMTI, ISMTI, CPT, etc.
- **Experimental Suite**: 
    - Parallelized simulation for scalability tests.
    - Automated sensitivity and robustness analysis.
    - Publication-quality figure generation (IEEE/ACM style).

### Project Structure
- `framework.py`: The universal physics kernel (Simulation Engine).
- `lods_mti_algo.py`: Core implementation of the Lods-mTI algorithm.
- `Algorithm_Config.py`: centralized configuration for algorithms and plotting styles.
- `Run_Test.py`: Robustness sanity check (100-round loop).
- `Run_All_Figures.py`: Batch processor for generating all paper figures.
- `Exp*.py`: Scripts for various experimental scenarios (Recall, Throughput, Drift, etc.).

### Quick Start
1. **Prerequisites**:
   ```bash
   pip install pandas matplotlib matplotlib-inline seaborn numpy
   ```
2. **Run a Check**:
   ```bash
   python Run_Test.py
   ```
3. **Run Full Experimental  Figures**:
   ```bash
   python Run_All_Figures.py
   ```

---

## 简体中文

### 项目简介
**Lods-mTI** (基于容错开环检测系统的 RFID 缺失标签识别) 是一个专为大规模 RFID 系统设计的高性能研究框架。该项目致力于在存在噪声、时钟漂移和突发擦除等物理层损伤的环境下，实现高可靠的缺失标签检测。

本仓库的核心是 **Lods-mTI 算法**，该算法采用基于自适应树结构的开环架构和多重投票机制，在复杂环境下依然能保持极高的识别精度和系统吞吐量。

### 核心特性
- **高保真物理内核**: 通用仿真引擎，支持信道误码 (BER)、时钟漂移、突发擦除、捕获效应及能耗追踪。
- **自适应投票机制**: 根据环境噪声强度动态调整验证密度 ($\rho$)，平衡可靠性与效率。
- **丰富的对比算法**: 集成了当前学术界主流算法：CR-MTI, ECUMI, CTMTI, ISMTI, CPT 等。
- **完整的实验套件**: 
    - 支持多进程并行仿真，提升大规模测试效率。
    - 自动化敏感性与鲁棒性分析。
    - 自动生成符合 IEEE/ACM 期刊标准的学术图表。

### 项目结构
- `framework.py`: 通用物理仿真内核 (仿真引擎)。
- `lods_mti_algo.py`: Lods-mTI 算法的核心实现。
- `Algorithm_Config.py`: 算法参数与绘图样式的统一配置中心。
- `Run_Test.py`: 鲁棒性压力测试工具 (支持百轮循环验证)。
- `Run_All_Figures.py`: 批量绘图调度器，一键生成所有实验图表。
- `Exp*.py`: 针对不同维度的实验脚本 (召回率、吞吐量、时钟漂移等)。

### 快速开始
1. **安装依赖**:
   ```bash
   pip install pandas matplotlib matplotlib-inline seaborn numpy
   ```
2. **针对单个算法的可行性测试**:
   ```bash
   python Run_Test.py
   ```
3. **运行完整实验绘图**:
   ```bash
   python Run_All_Figures.py
   ```

---

## Citation
If you find this work helpful in your research, please consider citing it as:
```
Hongquan Zhou, Xiaolin Jia, Zhong Du, et al. LODS-MTI: A Link-Adaptive, 0rthogonal, and De-slotted Protocol for Robust and Fast RFID Missing Tag Identification. TechRxiv. January 28, 2026.
```

