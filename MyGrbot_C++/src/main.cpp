#include <iostream>
#include "grbot.hpp"

int main() {
    processor.load("../data/points_data.csv");                 //重新加载CSV数据
    PathFinder finder;
        int get_int_data = processor.get_index_by_name("Y2");         //通过地址名字获取ID
        int get_int_data_2 = processor.get_index_by_name("Y10");   

        auto route = finder.find_shortest(get_int_data, get_int_data_2);     //输入起点与目标的ID，返回结构体包含:路径ID一维容器与累计距离的数据，
        std::vector<std::vector<double>> path_data = finder.getSelectedPaths(route.path);      //通过路径ID一维容器，返回二维容器，每个子容器包含X,Y,角度（即路径点）
        // 输出结果
        for (const auto& vec : path_data) {
                for (const auto& val : vec) {
                    std::cout << val << ",";
                }
            std::cout << std::endl;
        }
    return 0;
}
