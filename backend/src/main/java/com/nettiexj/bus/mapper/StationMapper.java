package com.nettiexj.bus.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nettiexj.bus.dto.RouteVO;
import com.nettiexj.bus.dto.StationParkingAvgVO;
import com.nettiexj.bus.dto.StationRankVO;
import com.nettiexj.bus.dto.StationVO;
import com.nettiexj.bus.entity.Station;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface StationMapper extends BaseMapper<Station> {

    /**
     * 查询所有站点，附带经过的线路数量
     */
    List<StationVO> selectAllWithRouteCount();

    /**
     * 查询某站点的所有途经线路
     */
    List<RouteVO> selectRoutesByStationId(@Param("stationId") Integer stationId);

    /**
     * 查询某线路经过的所有站点（按顺序）
     */
    List<Station> selectStationsByRouteId(@Param("routeId") Integer routeId);

    /**
     * 站点停靠次数全量排行
     */
    List<StationRankVO> selectTopByParkingCount();

    /**
     * 站点平均停靠时长全量排行
     */
    List<StationParkingAvgVO> selectTopByParkingAvgDuration();

    List<StationParkingAvgVO> selectParkingScatter();

    List<com.nettiexj.bus.dto.PeakStationVO> selectPeakComparison(@Param("topN") Integer topN);

    List<com.nettiexj.bus.dto.HourlyCountVO> selectHourlyCount(@Param("stationId") Integer stationId);

    List<com.nettiexj.bus.dto.TransferHubVO> selectTransferHubs(@Param("topN") Integer topN);

    /** 枢纽排行：从 section 表统计途经线路数（比 route_station 完整） */
    List<StationRankVO> selectHubRanking();

    List<com.nettiexj.bus.dto.ClusterParkingVO> selectClusterParkingStats();

    List<com.nettiexj.bus.dto.StationAnalysisVO> selectStationAnalysisByRouteId(@Param("routeId") Integer routeId);
}
