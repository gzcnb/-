/* 
 * @sentence  Looking into your past is the only way to discover your future.
 * @class 读取CSV文件并处理存入CSVRecord容器
 * @brief    
 *     CSVProcessor processor;                               // 创建对象
 * @function
 *     processor.load("../include/grbot.csv");               // 定义类的时候会执行一次，无需手动 加载CSV文件并存入容器
 *     auto tuo0 = processor.get_dataset();                  // 获取容器数据
 *     int tuo1 = processor.get_index_by_name("N1");         // 通过名字获取索引
 *     std::string tuo2 = processor.get_name_by_index(2);    // 通过索引获取名字
 *     processor.save_with_backup("grbot_new.csv");          // 生成新的文件
 *
 *
 * @class 生成图结构、计算最短路径、通过路径合成容器坐标
 * @brief    
 *     PathFinder finder("../include/grbot.csv");                   // 创建对象
 * @function
 *     NavigationResult route = finder.find_shortest(0, 1);                     // 查找最短路径 （起点，终点）
 *     std::vector<std::vector<double>> path_data = finder.getSelectedPaths(route.path);   //合成坐标容器
 * 日期：2025-07-2
 * 署名：Azitide
 * 版本：3.1
 */
#pragma once
#include <vector>
#include <string>
#include <unordered_set>
#include <unordered_map>
#include <sstream>
#include <fstream>
#include <iomanip>                       
#include <filesystem>
#include <stdexcept>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <mutex>
#include <memory>
#include <optional>
#include <queue>

namespace fs = std::filesystem;

struct CSVRecord {
    int index;
    double x;
    double y;
    double angle;
    std::string name;
    std::unordered_set<int> unidirectional_deps;
};

class CSVProcessor {
private:
    std::vector<CSVRecord> dataset;
    std::unordered_map<std::string, int> name_to_index;
    std::unordered_map<int, std::string> index_to_name;
    std::unordered_map<int, std::vector<double>> index_to_path;
    bool is_loaded = false;

    CSVProcessor(const std::string& csv_path);
    CSVProcessor(const CSVProcessor&) = delete;
    void operator=(const CSVProcessor&) = delete;
    
    double parse_expression(const std::string& expr);
    std::unordered_set<int> parse_dependencies(const std::string& str);

public:
    static CSVProcessor& GetInstance(const std::string& csv_path = "");

    void load(const fs::path& input_path);
    void save_with_backup(const fs::path& output_path);
    void add_operation(const std::string& name, double dx, double dy);
    
    int get_index_by_name(const std::string& name) const;
    std::string get_name_by_index(int index) const;
    const std::vector<CSVRecord>& get_dataset() const;
    std::vector<double> get_index_by_ptah(int index) const;
    
    static std::string serialize_deps(const std::unordered_set<int>& deps);
};

// 声明全局实例（在cpp中定义）
extern CSVProcessor& processor;


class PathFinder {
    public:
        struct Node {
            int index;
            double x;
            double y;
            double physical_distance(const Node& other) const;
        };
    
        struct PathResult {
            double distance;
            std::optional<int> predecessor;
        };
    
        struct NavigationResult {
            std::vector<int> path;
            double distance;
            bool reachable;
        };
        
        PathFinder();
        NavigationResult find_shortest(int start, int target);
        std::vector<std::vector<double>> getSelectedPaths(const std::vector<int>& indices);
        
    private:
        using Graph = std::unordered_map<int, std::vector<std::pair<int, double>>>;
        using ResultMap = std::unordered_map<int, PathResult>;
        
        Graph nav_graph;
        
        void build_graph(const std::vector<CSVRecord>& records);
        ResultMap dijkstra(int start);
        std::vector<int> reconstruct_path(const ResultMap& results, int target);
    };