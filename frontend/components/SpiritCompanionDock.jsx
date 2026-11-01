import { useEffect, useState } from "react";
import styles from "./SpiritCompanionDock.module.css";

const DIALOGUE = {
  idle: {
    girl: "Hi！我是小银，您的专属金融精灵哦~ (◍•ᴗ•◍)",
    boy: "我是安全护航员，系统正常。",
    girlTag: "在线陪伴",
    boyTag: "安全守护",
  },
  thinking: {
    girl: "正在为您构建 Financial DAG... 🧠",
    boy: "沙盘推演中，正在校验资金安全边界...",
    girlTag: "正在思考",
    boyTag: "任务运行中",
  },
  alert: {
    girl: "哎呀，遇到高风险交易啦！(⊙_⊙)",
    boy: "🚨 危险！已触发防御机制，请进行身份核验！",
    girlTag: "风险提醒",
    boyTag: "安全拦截",
  },
  success: {
    girl: "耶！任务安全完成~ 🎉",
    boy: "✅ 审计日志已记录。",
    girlTag: "任务完成",
    boyTag: "审计已记录",
  },
};

export default function SpiritCompanionDock({
  mood = "idle",
  activeScenario = null,
  showMfa = false,
  autoOpen = false,
}) {
  const [open, setOpen] = useState(false);

  const isAlert = showMfa || mood === "alert";
  const isThinking = autoOpen || mood === "thinking";
  const effectiveMood = isAlert
    ? "alert"
    : mood === "success"
      ? "success"
      : isThinking
        ? "thinking"
        : "idle";

  const travelDialogue = {
    girl: isThinking
      ? "正在把固定支出和旅行目标放进同一张资金沙盘…"
      : "房贷和日常开销先稳稳留好，再一起安排旅行预算哦！",
    boy: isThinking
      ? "正在校验最低流动性与预算边界…"
      : "固定支出与最低流动性优先保护。",
    girlTag: isThinking ? "规划计算中" : "资金规划",
    boyTag: isThinking ? "安全约束" : "沙盘护航",
  };

  const dialogue = isAlert
    ? DIALOGUE.alert
    : mood === "success"
      ? DIALOGUE.success
      : activeScenario === "travel"
        ? travelDialogue
        : isThinking
          ? DIALOGUE.thinking
          : DIALOGUE.idle;

  // 仅在真实业务运行或 MFA 风险状态时自动召唤；普通初始状态保持收起。
  useEffect(() => {
    if (isAlert || isThinking) {
      setOpen(true);
    }
  }, [isAlert, isThinking]);

  const closePanel = () => setOpen(false);

  return (
    <div className={styles.dockRoot} data-mood={effectiveMood}>
      <button
        type="button"
        className={`${styles.orb} ${open ? styles.orbOpen : ""} ${isAlert ? styles.orbAlert : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "收起双精灵面板" : "召唤双精灵面板"}
        aria-expanded={open}
        aria-controls="zhiyintong-spirit-panel"
        title={open ? "收起数字管家" : "召唤数字管家"}
      >
        <span className={styles.orbHalo} aria-hidden="true" />
        <span className={styles.orbCore} aria-hidden="true">
          <span className={styles.orbGlyph}>✦</span>
        </span>
        {isAlert && <span className={styles.orbAlertDot}>!</span>}
      </button>

      <section
        id="zhiyintong-spirit-panel"
        className={[
          styles.panel,
          open ? styles.panelOpen : "",
          isAlert ? styles.panelAlert : "",
          isThinking ? styles.panelThinking : "",
          mood === "success" ? styles.panelSuccess : "",
        ].filter(Boolean).join(" ")}
        aria-label="智银通双数字精灵"
        aria-live="polite"
        aria-hidden={!open}
      >
        <header className={styles.panelHeader}>
          <div className={styles.panelHeading}>
            <span className={styles.liveDot} />
            <span>双数字管家</span>
            <small>{isAlert ? "风险预警" : isThinking ? "协作中" : mood === "success" ? "已完成" : "在线"}</small>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={closePanel}
            aria-label="关闭精灵面板"
            tabIndex={open ? 0 : -1}
          >
            ×
          </button>
        </header>

        <div className={styles.companionGrid}>
          <article className={styles.companion}>
            <div className={`${styles.speech} ${styles.speechGirl} ${isAlert ? styles.speechAlert : ""}`}>
              <div className={styles.speechHeading}>
                <b>小银 · 金融精灵</b>
                <span>{dialogue.girlTag}</span>
              </div>
              <p>{dialogue.girl}</p>
              {isThinking && !isAlert && (
                <span className={styles.thinkingDots} aria-label="正在思考">
                  <i /><i /><i />
                </span>
              )}
              {isAlert && <span className={styles.alertMark} aria-hidden="true">!</span>}
            </div>
            <div className={`${styles.artStage} ${styles.girlStage}`}>
              <img
                className={`${styles.characterArt} ${styles.girlArt} ${isThinking ? styles.artThinking : ""} ${isAlert ? styles.artAlert : ""} ${mood === "success" ? styles.artSuccess : ""}`}
                src="/girl-new.png?v=20261101-glass2"
                alt="小银，白蓝配色的金融精灵女孩立绘"
                draggable="false"
                loading="eager"
              />
              {mood === "success" && (
                <span className={styles.successStars} aria-hidden="true">
                  <i>✦</i><i>✧</i><i>✦</i>
                </span>
              )}
            </div>
          </article>

          <article className={styles.companion}>
            <div className={`${styles.speech} ${styles.speechBoy} ${isAlert ? styles.speechBoyAlert : ""}`}>
              <div className={styles.speechHeading}>
                <b>安全护航员</b>
                <span>{dialogue.boyTag}</span>
              </div>
              <p>{dialogue.boy}</p>
              {isThinking && !isAlert && (
                <span className={`${styles.thinkingDots} ${styles.guardianDots}`} aria-label="正在校验">
                  <i /><i /><i />
                </span>
              )}
            </div>
            <div className={`${styles.artStage} ${styles.boyStage}`}>
              <span className={styles.radarRing} aria-hidden="true" />
              <img
                className={`${styles.characterArt} ${styles.boyArt} ${isThinking ? styles.artThinking : ""} ${isAlert ? styles.artAlert : ""}`}
                src="/boy-new.png?v=20261101-glass2"
                alt="安全护航员，深蓝制服的男性数字管家立绘"
                draggable="false"
                loading="eager"
              />
              {isAlert && <span className={styles.warningLines} aria-hidden="true"><i /><i /><i /></span>}
            </div>
          </article>
        </div>
      </section>
    </div>
  );
}
