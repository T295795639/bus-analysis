package com.nettiexj.bus.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nettiexj.bus.dto.SectionDrivingVO;
import com.nettiexj.bus.dto.SectionPathVO;
import com.nettiexj.bus.entity.Section;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface SectionMapper extends BaseMapper<Section> {

    List<SectionDrivingVO> selectDrivingStats(@Param("timeRange") String timeRange,
                                              @Param("topN") Integer topN);

    List<SectionPathVO> selectPathsByStationId(@Param("stationId") Integer stationId);

    List<SectionPathVO> selectPathsByRouteId(@Param("routeId") Integer routeId);

    List<com.nettiexj.bus.dto.SectionAnalysisRawVO> selectSectionAnalysisByRouteId(@Param("routeId") String routeId,
                                                                                   @Param("direction") String direction);

    LocalDateTime selectRouteDrivingMinTime(@Param("routeNumber") String routeNumber);

    LocalDateTime selectRouteDrivingMaxTime(@Param("routeNumber") String routeNumber);

    List<SectionPathVO> selectAllPaths();
}
