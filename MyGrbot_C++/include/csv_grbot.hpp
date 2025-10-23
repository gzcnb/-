/* 
 * @sentence  Looking into your past is the only way to discover your future.
 * @class 读取CSV文件并处理存入CSVRecord容器
 * @brief    
 *     CSVProcessor processor;                               // 创建对象
 * @function
 *     processor.load("../include/grbot.csv");               // 加载CSV文件并存入容器
 *     auto tuo0 = processor.get_dataset();                  // 获取容器数据
 *     auto tuo1 = processor.get_index_by_name("N1");        // 通过名字获取索引
 *     auto tuo2 = processor.get_name_by_index(2);           // 通过索引获取名字
 *     auto tuo3 = processor.get_index_by_ptah(1])           // 通过索引获取坐标X\Y\Angle
 * 
 * 日期：2025-05-10
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


struct CSVRecord {
    int index;
    double x;
    double y;
    double angle;
    std::string name;
    std::unordered_set<int> bidirectional_deps;
    std::unordered_set<int> unidirectional_deps;
};

// 在文件顶部添加命名空间别名
namespace fs = std::filesystem;

class CSVProcessor {
private:
    std::vector<CSVRecord> dataset;
    std::unordered_map<std::string, int> name_to_index;
    std::unordered_map<int, std::string> index_to_name;
    std::unordered_map<int, std::vector<double>> index_to_path;
    
    // 增强表达式解析
    // 表达式解析增强
    double parse_expression(const std::string& expr) {
        if (expr.empty()) {
            std::cerr << "空表达式" << std::endl;
            return 0.0;
        }
        
        try {
            std::string clean_expr = expr;
            clean_expr.erase(std::remove(clean_expr.begin(), clean_expr.end(), ' '), clean_expr.end());
            
            size_t op_pos = clean_expr.find_first_of("+-", 1);
            if (op_pos != std::string::npos) {
                double a = std::stod(clean_expr.substr(0, op_pos));
                double b = std::stod(clean_expr.substr(op_pos + 1));
                return (clean_expr[op_pos] == '+') ? (a + b) : (a - b);
            }
            return std::stod(clean_expr);
        } catch (const std::exception& e) {
            std::cerr << "表达式解析失败: " << expr << std::endl;
            return 0.0;
        }
    }

    // 依赖关系解析增强
    std::unordered_set<int> parse_dependencies(const std::string& str) {
        std::unordered_set<int> deps;
        if (str.empty()) return deps;

        const std::string delimiter = "、"; // UTF-8中文顿号
        size_t start = 0;
        size_t end = str.find(delimiter);
        
        while (end != std::string::npos) {
            std::string item = str.substr(start, end - start);
            if (!item.empty()) {
                try {
                    deps.insert(std::stoi(item));
                } catch (...) {
                    std::cerr << "无效依赖项: " << item << std::endl;
                }
            }
            start = end + delimiter.length();
            end = str.find(delimiter, start);
        }
        // 处理最后一项
        std::string last_item = str.substr(start);
        if (!last_item.empty()) {
            try {
                deps.insert(std::stoi(last_item));
            } catch (...) {
                std::cerr << "无效依赖项: " << last_item << std::endl;
            }
        }
        return deps;
    }

public: 
    // load函数读取写入容器
    void load(const fs::path& input_path = "../example/grobot.csv") {
        if (!fs::exists(input_path)) throw std::runtime_error("文件不存在");
        
        std::ifstream file(input_path);
        std::string line;
        
        // 跳过XML标签
        while (std::getline(file, line)) {
            if (line.find("<Sheet1>") != std::string::npos) continue;
            if (line.find("</Sheet1>") != std::string::npos) continue;
            break;
        }

        // 跳过表头行
        if (std::getline(file, line) && line.find("Index") != std::string::npos) {
            // 读取表头行并跳过
        }

        // 使用逗号分割字段
        do {
            CSVRecord record;
            std::vector<std::string> columns;
            std::istringstream iss(line);
            std::string cell;
            
            while (std::getline(iss, cell, ',')) {
                // 去除首尾空格
                cell.erase(0, cell.find_first_not_of(" \t\n\r"));
                cell.erase(cell.find_last_not_of(" \t\n\r") + 1);
                columns.push_back(cell);
            }

            if (columns.size() >= 7) {
                try {
                    record.index = std::stoi(columns[0]);
                    record.x = parse_expression(columns[1]);
                    record.y = parse_expression(columns[2]);
                    record.angle = std::stoi(columns[3]);
                    record.name = columns[4];
                    record.bidirectional_deps = parse_dependencies(columns[5]);
                    record.unidirectional_deps = parse_dependencies(columns[6]);

                    // 确保索引唯一性
                    if (index_to_name.find(record.index) != index_to_name.end()) {
                        throw std::runtime_error("重复的索引: " + std::to_string(record.index));
                    }

                    // 建立双向映射
                    name_to_index[record.name] = record.index;
                    index_to_name[record.index] = record.name;

                    //存入点位
                    index_to_path[record.index] = {record.x, record.y, record.angle};
                    
                    dataset.push_back(record);
                    name_to_index[record.name] = dataset.size() - 1;
                } catch (const std::exception& e) {
                    std::cerr << "行解析失败: " << line << std::endl;
                }
            }
        } while (std::getline(file, line));
    }

    void save_with_backup(const fs::path& output_path) {
        // 检查文件是否存在再备份
        // if (fs::exists(output_path)) {
        //     const auto backup_path = output_path.parent_path() / (output_path.stem().string() + ".txt");
        //     fs::copy_file(output_path, backup_path, fs::copy_options::overwrite_existing);
        // }
        // 写入新文件
        std::ofstream file(output_path);
        // 写入表头
        file << "Index,X,Y,Angle,名称,双向依赖关系,单向依赖关系\n";
        for (const auto& record : dataset) {
            file << std::fixed << std::setprecision(2)
                 << record.index << ","
                 << record.x << ","
                 << record.y << ","
                 << record.angle << ","
                 << record.name << ",";
            
            // 序列化依赖关系
            auto serialize_deps = [](const auto& deps) {
                std::stringstream ss;
                std::vector<int> sorted(deps.begin(), deps.end());
                std::sort(sorted.begin(), sorted.end());
                for (size_t i=0; i<sorted.size(); ++i) {
                    ss << sorted[i] << (i == sorted.size()-1 ? "" : "、");
                }
                return ss.str();
            };

            file << serialize_deps(record.bidirectional_deps) << ","
                 << serialize_deps(record.unidirectional_deps) << "\n";
        }
        file << "</Sheet1>\n";
    }

    // 添加运算操作 && 通过名称查找并修改
    void add_operation(const std::string& name, double dx, double dy) {
        auto& record = dataset[name_to_index.at(name)];
        // 使用std::round需要包含cmath
        record.x = std::round((record.x + dx) * 100) / 100;
        record.y = std::round((record.y + dy) * 100) / 100;
    }

    // 通过索引查找并修改 & 新增双向查找接口
    int get_index_by_name(const std::string& name) const {
        if (name_to_index.find(name) == name_to_index.end()) {
            std::cerr << "找不到名称对应的索引: " << name << std::endl;
        }
        return name_to_index.at(name);
    }
    std::string get_name_by_index(int index) const {
        if (index_to_name.find(index) == index_to_name.end()) {
            std::cerr << "找不到索引对应的名称: " << index << std::endl;
        }
        return index_to_name.at(index);
    }
    const std::vector<CSVRecord>& get_dataset() const {
        return dataset;
    }

    std::vector<double> get_index_by_ptah(int index) const {
        if (index_to_path.find(index) == index_to_path.end()) {
            std::cerr << "索引 " << index << " 对应的路径不存在" << std::endl;
            return {};
        }
        return index_to_path.at(index);
    }
    // 序列化依赖关系
    static std::string serialize_deps(const std::unordered_set<int>& deps) {
        std::vector<int> sorted(deps.begin(), deps.end());
        std::sort(sorted.begin(), sorted.end());
        std::stringstream ss;
        for (size_t i = 0; i < sorted.size(); ++i) {
            ss << sorted[i] << (i == sorted.size()-1 ? "" : "、");
        }
        return ss.str();
    }
};

//演示代码
int csv_main() {
    CSVProcessor processor;
    try {
        processor.load("../include/grbot.csv");
        
           // 通过名称查索引
           std::cout << "N1 的索引是: " << processor.get_index_by_name("N1") << std::endl;
           // 通过索引查名称
           std::cout << "索引2 的名称是: " << processor.get_name_by_index(2) << std::endl;

           // 在外部访问数据集
           auto tuo = processor.get_dataset();
           for (const auto& record : tuo) {
            std::cout << "索引:" << record.index 
                      << " X:"  << record.x
                      << " Y:" << record.y
                      << " 角度:" << record.angle
                      << " 名称:" << record.name 
                      << " 双向依赖:" << CSVProcessor::serialize_deps(record.bidirectional_deps)
                      << " 单向依赖:" << CSVProcessor::serialize_deps(record.unidirectional_deps)
                      << std::endl;
            }
        processor.save_with_backup("grbot_new.csv");
    } catch (const std::exception& e) {
        std::cerr << "处理错误: " << e.what() << std::endl;
    }
    return 0;
}