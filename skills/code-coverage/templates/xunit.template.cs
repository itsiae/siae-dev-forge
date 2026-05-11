// Use this template for: ASP.NET Core, Azure Functions, .NET 8+.
// Requires: xunit, xunit.runner.visualstudio, Moq, coverlet.msbuild.
// Replace all {{PLACEHOLDER}} tokens before use.

using System;
using System.Threading;
using System.Threading.Tasks;
using Moq;
using Xunit;
using FluentAssertions;

using {{NamespaceUnderTest}};

namespace {{TestNamespace}};

public class {{ClassName}}Tests
{
    private readonly Mock<{{IDepInterface}}> _{{depMockField}};
    private readonly {{ClassName}} _sut;

    public {{ClassName}}Tests()
    {
        _{{depMockField}} = new Mock<{{IDepInterface}}>();
        _sut = new {{ClassName}}(_{{depMockField}}.Object);
    }

    // ─── Happy Path ───────────────────────────────────────────────────────────

    [Fact]
    public async Task {{MethodName}}_ShouldReturn{{HappyPathResult}}_WhenInputIsValid()
    {
        // Arrange
        var input = {{HAPPY_PATH_INPUT}};
        var expected = {{EXPECTED_OUTPUT}};
        _{{depMockField}}
            .Setup(d => d.{{DepMethod}}(It.IsAny<{{InputType}}>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync({{DEP_RETURN_VALUE}});

        // Act
        var result = await _sut.{{MethodName}}(input, CancellationToken.None);

        // Assert
        result.Should().BeEquivalentTo(expected);
        _{{depMockField}}.Verify(
            d => d.{{DepMethod}}(input, It.IsAny<CancellationToken>()),
            Times.Once);
    }

    // ─── Edge Case 1: empty / null safe ───────────────────────────────────────

    [Fact]
    public async Task {{MethodName}}_ShouldReturnDefault_WhenInputIsEmpty()
    {
        // Arrange
        var emptyInput = {{EDGE_CASE_1_INPUT}};
        _{{depMockField}}
            .Setup(d => d.{{DepMethod}}(It.IsAny<{{InputType}}>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync({{EDGE_CASE_1_DEP_RETURN}});

        // Act
        var result = await _sut.{{MethodName}}(emptyInput, CancellationToken.None);

        // Assert
        result.Should().BeEquivalentTo({{EDGE_CASE_1_EXPECTED}});
    }

    // ─── Edge Case 2: boundary ────────────────────────────────────────────────

    [Theory]
    [InlineData({{EDGE_CASE_2_VALUE_1}})]
    [InlineData({{EDGE_CASE_2_VALUE_2}})]
    public async Task {{MethodName}}_ShouldHandleBoundaryValues({{InputType}} boundaryInput)
    {
        // Arrange
        _{{depMockField}}
            .Setup(d => d.{{DepMethod}}(It.IsAny<{{InputType}}>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync({{EDGE_CASE_2_DEP_RETURN}});

        // Act
        var result = await _sut.{{MethodName}}(boundaryInput, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
    }

    // ─── Negative Path: throws on invalid input ───────────────────────────────

    [Fact]
    public async Task {{MethodName}}_ShouldThrow{{ExceptionType}}_When{{NegativeConditionName}}()
    {
        // Arrange
        _{{depMockField}}
            .Setup(d => d.{{DepMethod}}(It.IsAny<{{InputType}}>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new {{ExceptionType}}("{{ERROR_MESSAGE}}"));

        // Act
        var act = async () => await _sut.{{MethodName}}({{INVALID_INPUT}}, CancellationToken.None);

        // Assert
        await act.Should().ThrowAsync<{{ExceptionType}}>()
            .WithMessage("*{{ERROR_MESSAGE}}*");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public async Task {{MethodName}}_ShouldThrowArgumentException_WhenInputIsNullOrEmpty(
        string? nullOrEmpty)
    {
        // Act
        var act = async () => await _sut.{{MethodName}}(nullOrEmpty!, CancellationToken.None);

        // Assert
        await act.Should().ThrowAsync<ArgumentException>();
    }

    // ─── Cancellation token test ──────────────────────────────────────────────

    [Fact]
    public async Task {{MethodName}}_ShouldThrowOperationCancelled_WhenTokenCancelled()
    {
        // Arrange
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        _{{depMockField}}
            .Setup(d => d.{{DepMethod}}(It.IsAny<{{InputType}}>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new OperationCanceledException());

        // Act
        var act = async () => await _sut.{{MethodName}}({{HAPPY_PATH_INPUT}}, cts.Token);

        // Assert
        await act.Should().ThrowAsync<OperationCanceledException>();
    }
}
