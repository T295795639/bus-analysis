package com.nettiexj.bus.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nettiexj.bus.dto.SectionDrivingVO;
import com.nettiexj.bus.dto.SectionPathVO;
import com.nettiexj.bus.entity.Section;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SectionMapper extends BaseMapper<Section> {

    List<SectionDrivingVO> selectDrivingStats(@Param("timeRange") String timeRange,
                                              @Param("topN") Integer topN);

    /** 按线路查询有序路段 path（用于前端绘制真实路形） */
    List<SectionPathVO> selectPathsByRouteId(@Param("routeId") Integer routeId);

    /** 路线分析：路段 + 平均行驶时长（path 为原始 JSON 字符串） */
    List<com.nettiexj.bus.dto.SectionAnalysisRawVO> selectSectionAnalysisByRouteId(@Param("routeId") Integer routeId);
}
