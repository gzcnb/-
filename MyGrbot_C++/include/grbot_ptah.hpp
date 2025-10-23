/* 
 * @sentence  Looking into your past is the only way to discover your future.
 * @class 生成图结构、计算最短路径、通过路径合成容器坐标
 * @brief    
 *     PathFinder finder("../include/grbot.csv");                   // 创建对象
 * @function
 *     auto route = finder.find_shortest(0, 1);                     // 查找最短路径 （起点，终点）
 * 日期：2025-05-11
 * 作者：Azitide
 * 版本：2.1
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
#include <optional>
#include "read_csvt.hpp"
#include <queue>

class PathFinder {
    public:
        struct Node {
            int index;
            double x;
            double y;
            double physical_distance(const Node& other) const {
                return std::hypot(x - other.x, y - other.y);
            }
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
    
        PathFinder(const std::string& csv_path) {
            CSVProcessor processor;
            processor.load(csv_path);
            build_graph(processor.get_dataset());
        }
    
        NavigationResult find_shortest(int start, int target) {
            NavigationResult result;
            auto path_result = dijkstra(start);
            
            if (auto it = path_result.find(target); it == path_result.end()) {
                result.reachable = false;
            } else {
                result.path = reconstruct_path(path_result, target);
                result.distance = it->second.distance;
                result.reachable = !result.path.empty();
            }
            return result;
        }
    
    private:
        using Graph = std::unordered_map<int, std::vector<std::pair<int, double>>>;
        using ResultMap = std::unordered_map<int, PathResult>;
    
        Graph nav_graph;
    
        private:
            // 构建图结构
            void build_graph(const std::vector<CSVRecord>& records) {
                std::unordered_map<int, Node> nodes;
                nav_graph.reserve(records.size() * 2);  // 预分配内存
                
                // 节点预处理
                for (const auto& r : records) {
                    // 修复坐标计算问题（假设CSVRecord已处理表达式）
                    nodes.emplace(r.index, Node{r.index, r.x, r.y});
                }
            
                // 构建邻接关系
                for (const auto& r : records) {
                    auto& edges = nav_graph[r.index];
                    
                    // 处理双向依赖（添加反向边优化）
                    for (int dep : r.bidirectional_deps) {
                        if (nodes.count(dep)) {
                            double weight = nodes[r.index].physical_distance(nodes[dep]);
                            edges.emplace_back(dep, weight);
                            nav_graph[dep].emplace_back(r.index, weight);
                        }
                    }
                    
                    // 修复单向依赖处理
                    std::vector<int> valid_deps;
                    for (int dep : r.unidirectional_deps) {
                        if (nodes.count(dep)) {
                            valid_deps.push_back(dep);
                            // 添加正向边
                            double weight = nodes[r.index].physical_distance(nodes[dep]);
                            edges.emplace_back(dep, weight);
                            
                            // 增加反向边过滤（防止反向边被添加）
                            auto& reverse_edges = nav_graph[dep];
                            reverse_edges.erase(
                                std::remove_if(reverse_edges.begin(), reverse_edges.end(),
                                    [&](const auto& e) { return e.first == r.index; }),
                                reverse_edges.end()
                            );
                        }
                    }
                }
            }
    
            // 计算最短路径
            ResultMap dijkstra(int start) {  // 修正参数列表
                struct QueueNode {
                    int id;
                    double dist;
                    bool operator>(const QueueNode& rhs) const { return dist > rhs.dist; }
                };
                
                ResultMap res;
                // 修正优先队列的模板参数
                std::priority_queue<QueueNode, 
                                    std::vector<QueueNode>, 
                                    std::greater<QueueNode>> pq;  // 添加模板类型参数
                // 使用成员变量nav_graph
                for (const auto& [id, _] : nav_graph) {
                    res[id] = {std::numeric_limits<double>::max(), std::nullopt};
                }
                res[start].distance = 0.0;
                pq.push({start, 0.0});
            
                while (!pq.empty()) {
                    auto [current_id, current_dist] = pq.top();
                    pq.pop();
            
                    if (current_dist > res[current_id].distance) continue;
            
                    if (auto it = nav_graph.find(current_id); it != nav_graph.end()) {
                        for (const auto& [neighbor, weight] : it->second) {
                            double new_dist = current_dist + weight;
                            if (new_dist < res[neighbor].distance) {
                                res[neighbor] = {new_dist, current_id};
                                pq.push({neighbor, new_dist});
                            }
                        }
                    }
                }
                return res;
            }
    
            // 路径重建函数
            std::vector<int> reconstruct_path(const ResultMap& results, int target) {
                std::vector<int> path;
                if (results.find(target) == results.end()) return path;
                
                int current = target;
                while (results.at(current).predecessor.has_value()) {
                    path.push_back(current);
                    current = results.at(current).predecessor.value();
                }
                path.push_back(current); // 动态获取实际起点
                std::reverse(path.begin(), path.end());
                return path;
            }
    };
    
    // 修改后的主函数
    int grbot_main() {
        CSVProcessor processor;
        processor.load("../include/grbot.csv");
        PathFinder finder("../include/grbot.csv");

        int get_int_data = processor.get_index_by_name("Y0");
        int get_int_data_2 = processor.get_index_by_name("U10");  
        auto route = finder.find_shortest(get_int_data_2, get_int_data);
        std::vector<std::vector<double>> path_data;
        if (route.reachable) {
            std::cout << "最短路径: ";
            for (size_t i = 0; i < route.path.size(); ++i) {
                std::cout << route.path[i] << (i == route.path.size()-1 ? "\n" : "->");
                path_data.push_back(processor.get_index_by_ptah(route.path[i]));
            }
            std::cout << "实际距离: " << std::fixed << std::setprecision(1) 
                      << route.distance << "厘米\n";
            // 输出结果
            for (const auto& vec : path_data) {
                    for (const auto& val : vec) {
                        std::cout << val << ",";
                    }
                    std::cout << std::endl;
                }
        }
        return 0;
    }