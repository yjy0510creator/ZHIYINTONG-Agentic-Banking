/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F4F7FA",
        ink: "#18263B",
        muted: "#8290A3",
        brand: {
          50: "#F1F6FE",
          100: "#E5EEFC",
          500: "#5C8DDA",
          600: "#4778C9",
          700: "#315FAE",
        },
        mint: "#EAF7F0",
        amber: "#FFF6E4",
        coral: "#FFF0F1",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 5px 26px rgba(25, 48, 79, 0.055)",
        float: "0 16px 44px rgba(25, 48, 79, 0.10)",
        blue: "0 10px 28px rgba(71, 120, 201, 0.17)",
      },
      borderRadius: {
        "2.5xl": "1.25rem",
        "3xl": "1.5rem",
      },
      letterSpacing: {
        apple: "-0.035em",
      },
    },
  },
  plugins: [],
};
