<template>
  <div class="app">
    <nav class="nav">
      <h1>南昌公交可视化</h1>
      <div class="links">
        <router-link to="/map">站点地图</router-link>
        <router-link to="/ranking">热度排行</router-link>
        <router-link to="/section">路段分析</router-link>
        <router-link to="/parking">停靠分析</router-link>
        <router-link to="/route">线路详情</router-link>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
.app { display: flex; flex-direction: column; height: 100vh; }
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px; background: #1f2937; color: white; flex-shrink: 0;
}
.nav h1 { font-size: 18px; font-weight: 600; }
.links a {
  color: #d1d5db; margin-left: 20px; text-decoration: none;
  padding: 6px 12px; border-radius: 4px; font-size: 14px;
}
.links a.router-link-active { background: #374151; color: white; }
</style>
