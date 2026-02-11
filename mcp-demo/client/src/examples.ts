import { MCPDemoClient } from './client.js';

export async function runExamples(client: MCPDemoClient) {
  console.log('\n🧪 运行 MCP Client 示例\n');
  console.log('=' .repeat(50));

  // 1. 列出工具
  console.log('\n📦 可用工具列表:');
  const tools = await client.listTools();
  tools.forEach((tool, i) => {
    console.log(`  ${i + 1}. ${tool.name}: ${tool.description}`);
  });

  // 2. 调用 calculate 工具
  console.log('\n🔧 调用 calculate 工具:');
  const calcResult = await client.callTool('calculate', {
    operation: 'multiply',
    a: 42,
    b: 100,
  });
  console.log('  结果:', calcResult.content[0].text);

  // 3. 调用 getWeather 工具
  console.log('\n🌤️  调用 getWeather 工具:');
  const weatherResult = await client.callTool('getWeather', {
    city: '上海',
    days: 3,
  });
  console.log('  结果:', weatherResult.content[0].text);

  // 4. 列出资源
  console.log('\n📚 可用资源列表:');
  const { resources, templates } = await client.listResources();
  resources.forEach((res, i) => {
    console.log(`  ${i + 1}. ${res.uri}: ${res.description}`);
  });
  console.log('\n  资源模板:');
  templates?.forEach((tpl, i) => {
    console.log(`  ${i + 1}. ${tpl.uriTemplate}: ${tpl.description}`);
  });

  // 5. 读取系统资源
  console.log('\n📖 读取 system://info:');
  const systemInfo = await client.readResource('system://info');
  const info = JSON.parse(systemInfo[0].text as string);
  console.log('  平台:', info.platform);
  console.log('  架构:', info.arch);
  console.log('  Node版本:', info.nodeVersion);

  // 6. 读取用户资料
  console.log('\n👤 读取 user://1/profile:');
  const userProfile = await client.readResource('user://1/profile');
  console.log('  内容:', userProfile[0].text);

  // 7. 列出提示模板
  console.log('\n📝 可用提示模板:');
  const prompts = await client.listPrompts();
  prompts.forEach((prompt, i) => {
    console.log(`  ${i + 1}. ${prompt.name}: ${prompt.description}`);
  });

  // 8. 获取代码审查提示
  console.log('\n💻 获取 codeReview 提示模板:');
  const codeReviewPrompt = await client.getPrompt('codeReview', {
    code: 'function add(a, b) { return a + b; }',
    language: 'javascript',
  });
  console.log('  提示内容预览:', codeReviewPrompt[0].content.text.substring(0, 100) + '...');

  // 9. 获取概念解释提示
  console.log('\n🎓 获取 explainConcept 提示模板:');
  const explainPrompt = await client.getPrompt('explainConcept', {
    concept: 'Model Context Protocol',
    level: 'beginner',
  });
  console.log('  提示内容预览:', explainPrompt[0].content.text.substring(0, 100) + '...');

  console.log('\n' + '='.repeat(50));
  console.log('✨ 所有示例运行完成!\n');
}
